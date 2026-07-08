import os
import logging
import random
import json
import hashlib
import asyncio
import yaml
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes, MessageHandler, filters
from io import BytesIO

load_dotenv()

from parser import get_new_posts, mark_posted
from media_manager import process_media
from llm_client import generate_tweet_text, select_best_post
from twitter_client import post_tweet
from config import load_config, CONFIG_PATH

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

PENDING_POSTS_FILE = "pending_posts.json"
IMAGES_DIR = "images"
os.makedirs(IMAGES_DIR, exist_ok=True)

bot_state = {
    "next_run_time": None,
    "last_run_time": None,
    "posts_published": 0,
    "cooldown_until": None
}

POST_HISTORY_FILE = "post_history.json"

def load_post_history() -> list:
    if os.path.exists(POST_HISTORY_FILE):
        try:
            with open(POST_HISTORY_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading post history: {e}")
    return []

def add_to_history(text: str):
    history = load_post_history()
    entry = {
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "text": text
    }
    history.insert(0, entry)
    history = history[:20]  # Keep last 20
    try:
        with open(POST_HISTORY_FILE, 'w') as f:
            json.dump(history, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving post history: {e}")

def load_pending_posts() -> dict:
    if os.path.exists(PENDING_POSTS_FILE):
        try:
            with open(PENDING_POSTS_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading pending posts: {e}")
    return {}

def save_pending_posts(pending: dict):
    try:
        with open(PENDING_POSTS_FILE, 'w') as f:
            json.dump(pending, f, indent=4)
    except Exception as e:
        logger.error(f"Error saving pending posts: {e}")

def parse_time(val: str) -> int:
    val = val.lower().strip()
    try:
        if val.endswith('h'): return int(float(val[:-1]) * 3600)
        if val.endswith('m'): return int(float(val[:-1]) * 60)
        if val.endswith('s'): return int(float(val[:-1]))
        return int(float(val))
    except Exception:
        return -1

def get_randomized_interval(bot_config: dict) -> int:
    interval = bot_config.get("interval")
    if isinstance(interval, list) and len(interval) == 2:
        return random.randint(min(interval), max(interval))
    elif isinstance(interval, int) and interval > 0:
        return interval
    return random.randint(5 * 3600, 8 * 3600)

def update_config_value(key: str, value: any):
    try:
        with open(CONFIG_PATH, 'r') as f:
            cfg = yaml.safe_load(f) or {}
        if "bot" not in cfg: cfg["bot"] = {}
        cfg["bot"][key] = value
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(cfg, f, allow_unicode=True)
        load_config.cache_clear()
    except Exception as e:
        logger.error(f"Error updating config silently: {e}")

# Global State
pending_posts = load_pending_posts()

def is_admin(update: Update) -> bool:
    admin_id = os.getenv("TELEGRAM_CHAT_ID")
    if not admin_id:
        return False
    chat_id = str(update.effective_chat.id)
    return chat_id == admin_id

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.message.reply_text("⛔ Unauthorized access.")
        return
        
    update_config_value("active", True)
        
    config = load_config()
    niche = config.get("bot", {}).get("niche", "Unknown")
    mode = config.get("bot", {}).get("mode", "Unknown")
    
    welcome_text = (
        "🤖 <b>Welcome to AI Twitter Bot Control Panel</b>\n\n"
        f"🎯 Current Niche: <code>{niche}</code>\n"
        f"⚙️ Operating Mode: <code>{mode}</code>\n\n"
        "Use the menu below to control the bot. Type /help to see all commands."
    )
    
    keyboard = [
        ["🔍 Find News", "📦 My Queue"],
        ["⏯ Pause / Start", "🤖 Auto-Post: ON/OFF"],
        ["⚙️ Settings"]
    ]
    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True)
    await update.message.reply_text(welcome_text, parse_mode='HTML', reply_markup=reply_markup)

async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    help_text = (
        "📖 <b>Available Commands:</b>\n"
        "/status - View bot health and schedule\n"
        "/parse (or /force) - Force an immediate news check\n"
        "/queue - Show pending posts\n"
        "/history - Show last published posts\n"
        "/sources - Show current RSS/Reddit sources\n"
        "/set_niche &lt;name&gt; - Change niche\n"
        "/set_mode &lt;auto|manual&gt; - Change mode\n"
        "/set_tone &lt;tone&gt; - Change tone of voice\n"
        "/set_prompt &lt;text&gt; - Set custom LLM instructions\n"
        "/set_interval &lt;time&gt; - Set post interval (e.g. 2h, 30m, 3600)\n"
        "/set_notify &lt;time&gt; - Set notify before post (e.g. 1h, 0)\n"
        "/add_rss &lt;url&gt; - Add RSS feed (manual mode)\n"
        "/remove_rss &lt;url&gt; - Remove RSS feed\n"
        "/add_sub &lt;name&gt; - Add subreddit (manual mode)\n"
        "/remove_sub &lt;name&gt; - Remove subreddit (manual mode)\n"
        "/clear_sources - Clear discovered sources cache\n"
        "/stop - Pause the bot\n"
        "/noaccept - Toggle Auto Post mode\n"
        "/help - Show this menu"
    )
    await update.message.reply_text(help_text, parse_mode='HTML')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
        
    config = load_config()
    niche = config.get("bot", {}).get("niche", "Unknown")
    
    last_run = bot_state['last_run_time'].strftime("%Y-%m-%d %H:%M:%S") if bot_state['last_run_time'] else "Never"
    next_run = bot_state['next_run_time'].strftime("%Y-%m-%d %H:%M:%S") if bot_state['next_run_time'] else "Not scheduled"
    
    cd = bot_state.get('cooldown_until')
    cd_text = f"\n💤 Cooldown Until: <code>{cd.strftime('%Y-%m-%d %H:%M:%S')}</code>" if cd and cd > datetime.now() else ""
    
    text = (
        "📊 <b>Bot Status</b>\n\n"
        f"🎯 Niche: <code>{niche}</code>\n"
        f"🕒 Last Check: <code>{last_run}</code>\n"
        f"⏳ Next Check: <code>{next_run}</code>{cd_text}\n"
        f"✅ Posts Published (this session): <code>{bot_state['posts_published']}</code>\n"
        f"📦 Pending Approvals: <code>{len(pending_posts)}</code>"
    )
    await update.message.reply_text(text, parse_mode='HTML')

async def force_check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
        
    await update.message.reply_text("🔄 Forcing an immediate news check. This might take a minute...")
    await check_news(context, manual=True)

async def update_config(update: Update, key: str, value: str):
    if not is_admin(update): return
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            cfg = yaml.safe_load(f) or {}
            
        if "bot" not in cfg:
            cfg["bot"] = {}
            
        cfg["bot"][key] = value
        
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(cfg, f, allow_unicode=True)
            
        load_config.cache_clear()
        await update.message.reply_text(f"✅ <b>Updated:</b> <code>{key}</code> = <code>{value}</code>", parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        await update.message.reply_text(f"❌ <b>Error updating config:</b> {e}", parse_mode='HTML')

async def set_niche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: <code>/set_niche &lt;name&gt;</code>", parse_mode='HTML')
        return
    await update_config(update, "niche", " ".join(context.args))

async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in ['auto', 'manual']:
        await update.message.reply_text("Usage: <code>/set_mode auto</code> or <code>/set_mode manual</code>", parse_mode='HTML')
        return
    await update_config(update, "mode", context.args[0])

async def set_tone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: <code>/set_tone &lt;description&gt;</code>", parse_mode='HTML')
        return
    await update_config(update, "tone_of_voice", " ".join(context.args))

async def set_prompt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: <code>/set_prompt &lt;instructions&gt;</code>", parse_mode='HTML')
        return
    await update_config(update, "prompt", " ".join(context.args))

async def set_interval(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: <code>/set_interval &lt;min_time&gt; [max_time]</code> (e.g., 1h 3h or 2h)", parse_mode='HTML')
        return
        
    if len(context.args) == 1:
        sec = parse_time(context.args[0])
        if sec <= 0:
            await update.message.reply_text("❌ Invalid time format.", parse_mode='HTML')
            return
        await update_config(update, "interval", sec)
    elif len(context.args) >= 2:
        sec1 = parse_time(context.args[0])
        sec2 = parse_time(context.args[1])
        if sec1 <= 0 or sec2 <= 0:
            await update.message.reply_text("❌ Invalid time format.", parse_mode='HTML')
            return
        await update_config(update, "interval", [min(sec1, sec2), max(sec1, sec2)])

async def set_notify(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: <code>/set_notify &lt;time&gt;</code> (e.g., 1h, 0)", parse_mode='HTML')
        return
    sec = parse_time(context.args[0])
    if sec < 0:
        await update.message.reply_text("❌ Invalid time format.", parse_mode='HTML')
        return
    await update_config(update, "notify_before", sec)

async def stop_bot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    update_config_value("active", False)
    await update.message.reply_text("⏸ <b>Bot Paused.</b> News checking suspended.", parse_mode='HTML')

async def toggle_auto_post(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    config = load_config()
    current = config.get("bot", {}).get("auto_post", False)
    new_val = not current
    update_config_value("auto_post", new_val)
    if new_val:
        await update.message.reply_text("✅ <b>Auto Post: ON</b> (No approval required)", parse_mode='HTML')
    else:
        await update.message.reply_text("❌ <b>Auto Post: OFF</b> (Manual approval required)", parse_mode='HTML')

async def clear_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    if os.path.exists("auto_sources.json"):
        os.remove("auto_sources.json")
        await update.message.reply_text("✅ <b>Cache cleared.</b> The bot will discover new sources on the next run.", parse_mode='HTML')
    else:
        await update.message.reply_text("ℹ️ Source cache is already empty.", parse_mode='HTML')

async def send_queue_item(bot, chat_id, index: int):
    if not pending_posts:
        await bot.send_message(chat_id=chat_id, text="📭 Post queue is empty.")
        return
        
    keys = list(pending_posts.keys())
    if index < 0: index = len(keys) - 1
    if index >= len(keys): index = 0
    
    url_key = keys[index]
    post = pending_posts[url_key]
    
    keyboard = [
        [
            InlineKeyboardButton("✅ Approve", callback_data=f"app_{url_key}"),
            InlineKeyboardButton("❌ Reject", callback_data=f"rej_{url_key}")
        ],
        [
            InlineKeyboardButton("🔄 Rewrite", callback_data=f"rew_{url_key}"),
            InlineKeyboardButton("⏸ Turn Off", callback_data=f"off_{url_key}")
        ],
        [
            InlineKeyboardButton("⬅️ Prev", callback_data=f"qpr_{index}"),
            InlineKeyboardButton(f"{index + 1}/{len(keys)}", callback_data="noop"),
            InlineKeyboardButton("Next ➡️", callback_data=f"qnx_{index}")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    message_text = f"📰 <b>Queued Post:</b>\n{post['title']}\n\n📝 <b>Generated Tweet:</b>\n{post['generated_tweet']}"
    
    img_path = os.path.join(IMAGES_DIR, f"{url_key}.jpg")
    if os.path.exists(img_path):
        try:
            with open(img_path, "rb") as img_file:
                await bot.send_photo(chat_id=chat_id, photo=BytesIO(img_file.read()), caption=message_text, reply_markup=reply_markup, parse_mode='HTML')
                return
        except Exception as e:
            logger.error(f"Error reading image: {e}")
            
    await bot.send_message(chat_id=chat_id, text=message_text, reply_markup=reply_markup, parse_mode='HTML')

async def show_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    await send_queue_item(context.bot, update.effective_chat.id, 0)

async def update_sources(update: Update, source_type: str, action: str, value: str):
    if not is_admin(update): return
    
    try:
        with open(CONFIG_PATH, 'r') as f:
            cfg = yaml.safe_load(f) or {}
            
        if "sources" not in cfg:
            cfg["sources"] = {"rss": [], "subreddits": []}
            
        sources_list = cfg["sources"].get(source_type, [])
        
        if action == "add":
            if value not in sources_list:
                sources_list.append(value)
                msg = f"✅ Added to {source_type}: <code>{value}</code>"
            else:
                msg = f"ℹ️ Already exists in {source_type}: <code>{value}</code>"
        elif action == "remove":
            if value in sources_list:
                sources_list.remove(value)
                msg = f"✅ Removed from {source_type}: <code>{value}</code>"
            else:
                msg = f"⚠️ Not found in {source_type}: <code>{value}</code>"
        else:
            msg = f"❌ Unknown action: {action}"
                
        cfg["sources"][source_type] = sources_list
        
        with open(CONFIG_PATH, 'w') as f:
            yaml.dump(cfg, f, allow_unicode=True)
            
        load_config.cache_clear()
        await update.message.reply_text(msg, parse_mode='HTML')
    except Exception as e:
        logger.error(f"Error updating sources: {e}")
        await update.message.reply_text(f"❌ <b>Error:</b> {e}", parse_mode='HTML')

async def add_rss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: <code>/add_rss &lt;url&gt;</code>", parse_mode='HTML')
        return
    await update_sources(update, "rss", "add", context.args[0])

async def remove_rss(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: <code>/remove_rss &lt;url&gt;</code>", parse_mode='HTML')
        return
    await update_sources(update, "rss", "remove", context.args[0])

async def add_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: <code>/add_sub &lt;name&gt;</code>", parse_mode='HTML')
        return
    await update_sources(update, "subreddits", "add", context.args[0])

async def remove_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Usage: <code>/remove_sub &lt;name&gt;</code>", parse_mode='HTML')
        return
    await update_sources(update, "subreddits", "remove", context.args[0])

async def show_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    
    config = load_config()
    mode = config.get("bot", {}).get("mode", "manual")
    
    sources = {"rss": [], "subreddits": []}
    if mode == "auto":
        if os.path.exists("auto_sources.json"):
            try:
                with open("auto_sources.json", "r") as f:
                    sources = json.load(f)
            except Exception:
                pass
    else:
        sources = config.get("sources", {})
        
    text = f"🔍 <b>Current Sources ({mode.upper()}):</b>\n\n"
    text += "<b>RSS:</b>\n" + ("\n".join(f"- {s}" for s in sources.get("rss", [])) or "None") + "\n\n"
    text += "<b>Subreddits:</b>\n" + ("\n".join(f"- {s}" for s in sources.get("subreddits", [])) or "None")
    
    await update.message.reply_text(text, parse_mode='HTML')

async def show_history(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    history = load_post_history()
    if not history:
        await update.message.reply_text("📭 Post history is empty.")
        return
        
    text = "📜 <b>Last 5 Published Posts:</b>\n\n"
    for idx, item in enumerate(history[:5]):
        text += f"🕒 <code>{item['time']}</code>\n📝 {item['text']}\n\n"
        
    await update.message.reply_text(text, parse_mode='HTML')

async def scheduled_check(context: ContextTypes.DEFAULT_TYPE):
    await check_news(context, manual=False)

async def trigger_manual_check(context: ContextTypes.DEFAULT_TYPE):
    await check_news(context, manual=True)

async def send_notification(context: ContextTypes.DEFAULT_TYPE):
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    notify_time = context.job.data
    if chat_id:
        try:
            config = load_config()
            if config.get("bot", {}).get("active", True):
                await context.bot.send_message(chat_id=chat_id, text=f"⏳ <b>Reminder:</b> Next post will be sent for approval in {notify_time/60:.0f} minutes!", parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error sending notification: {e}")

def schedule_next_check(context: ContextTypes.DEFAULT_TYPE, config: dict):
    bot_config = config.get("bot", {})
    interval_sec = get_randomized_interval(bot_config)
        
    logger.info(f"Next check scheduled in {interval_sec/3600:.2f} hours.")
    bot_state['next_run_time'] = datetime.now() + timedelta(seconds=interval_sec)
    context.job_queue.run_once(scheduled_check, interval_sec)
    
    notify = bot_config.get("notify_before", 3600)
    if notify > 0 and interval_sec > notify:
        notify_delay = interval_sec - notify
        context.job_queue.run_once(send_notification, notify_delay, data=notify)

async def check_news(context: ContextTypes.DEFAULT_TYPE, manual=False):
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        logger.error("TELEGRAM_CHAT_ID is not set! Please set it in .env")
        return

    config = load_config()
    bot_config = config.get("bot", {})
    
    cd = bot_state.get('cooldown_until')
    if not manual and cd and datetime.now() < cd:
        logger.info(f"Bot is on cooldown until {cd}. Skipping check.")
        schedule_next_check(context, config)
        return
        
    if not manual and not bot_config.get("active", True):
        logger.info("Bot is inactive. Skipping check.")
        schedule_next_check(context, config)
        return
        
    if not manual and len(pending_posts) >= bot_config.get("queue_limit", 3):
        logger.info("Queue limit reached (3). Skipping check.")
        schedule_next_check(context, config)
        return

    logger.info("Checking for new posts...")
    bot_state['last_run_time'] = datetime.now()
    
    try:
        posts = await asyncio.to_thread(get_new_posts)
        
        filtered_posts = []
        for p in posts:
            p_key = hashlib.sha256(p['url'].encode()).hexdigest()[:16]
            if p_key not in pending_posts:
                filtered_posts.append(p)
                
        if not filtered_posts:
            if manual:
                await context.bot.send_message(chat_id=chat_id, text="ℹ️ No new unposted news found.")
        else:
            logger.info(f"Selecting best post from {len(filtered_posts)} items...")
            best_post = await asyncio.to_thread(select_best_post, filtered_posts)
            
            logger.info(f"Processing post: {best_post['title']}")
            
            best_post = await asyncio.to_thread(process_media, best_post)
            tweet_text = await asyncio.to_thread(generate_tweet_text, best_post)
            best_post['generated_tweet'] = tweet_text
            
            url_key = hashlib.sha256(best_post['url'].encode()).hexdigest()[:16]
            img_path = os.path.join(IMAGES_DIR, f"{url_key}.jpg")
            
            if best_post.get('final_image_bytes'):
                try:
                    with open(img_path, "wb") as img_file:
                        img_file.write(best_post['final_image_bytes'])
                except Exception as e:
                    logger.error(f"Failed to save image for {url_key}: {e}")
            
            if bot_config.get("auto_post", False):
                success = await asyncio.to_thread(post_tweet, best_post['generated_tweet'], best_post.get('final_image_bytes'))
                if success:
                    bot_state['posts_published'] += 1
                    add_to_history(best_post['generated_tweet'])
                    
                    interval_sec = get_randomized_interval(bot_config)
                    bot_state['cooldown_until'] = datetime.now() + timedelta(seconds=interval_sec)
                    
                    await asyncio.to_thread(mark_posted, best_post['url'], best_post['source'])
                    await context.bot.send_message(chat_id=chat_id, text=f"✅ <b>Automatically Posted:</b>\n{best_post['title']}\n\n{best_post['generated_tweet']}", parse_mode='HTML')
                else:
                    await context.bot.send_message(chat_id=chat_id, text=f"⚠️ <b>Auto Post Failed:</b>\n{best_post['title']}", parse_mode='HTML')
                
                if 'final_image_bytes' in best_post and os.path.exists(img_path):
                    os.remove(img_path)
            else:
                post_for_json = best_post.copy()
                if 'final_image_bytes' in post_for_json:
                    del post_for_json['final_image_bytes']
                
                pending_posts[url_key] = post_for_json
                save_pending_posts(pending_posts)
                
                keyboard = [
                    [
                        InlineKeyboardButton("✅ Approve", callback_data=f"app_{url_key}"),
                        InlineKeyboardButton("❌ Reject", callback_data=f"rej_{url_key}")
                    ],
                    [
                        InlineKeyboardButton("🔄 Rewrite", callback_data=f"rew_{url_key}"),
                        InlineKeyboardButton("⏸ Turn Off", callback_data=f"off_{url_key}")
                    ]
                ]
                reply_markup = InlineKeyboardMarkup(keyboard)
                message_text = f"📰 <b>New Post:</b>\n{best_post['title']}\n\n📝 <b>Generated Tweet:</b>\n{tweet_text}"
                
                if best_post.get('final_image_bytes'):
                    await context.bot.send_photo(
                        chat_id=chat_id,
                        photo=BytesIO(best_post['final_image_bytes']),
                        caption=message_text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
                else:
                    await context.bot.send_message(
                        chat_id=chat_id,
                        text=message_text,
                        reply_markup=reply_markup,
                        parse_mode='HTML'
                    )
    except Exception as e:
        logger.error(f"Error during check_news: {e}")
        if manual:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error occurred: {e}")

    if not manual:
        schedule_next_check(context, config)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.callback_query.answer("⛔ Unauthorized.", show_alert=True)
        return
        
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if data.startswith("set_"):
        if data == "set_prompt":
            await query.message.reply_text("To change the prompt, use command:\n<code>/set_prompt &lt;your_new_prompt&gt;</code>", parse_mode='HTML')
        elif data == "set_interval":
            await query.message.reply_text("To change the interval, use command:\n<code>/set_interval &lt;time&gt;</code> (e.g. 2h, 30m)", parse_mode='HTML')
        elif data == "set_niche":
            await query.message.reply_text("To change the niche, use command:\n<code>/set_niche &lt;new_niche&gt;</code>", parse_mode='HTML')
        elif data == "set_mode":
            await query.message.reply_text("To change the mode, use command:\n<code>/set_mode auto</code> or <code>/set_mode manual</code>", parse_mode='HTML')
        return
        
    if len(data) < 5 or data[3] != '_':
        await query.answer("Invalid action data format.", show_alert=True)
        return
        
    action = data[:3]
    url_key = data[4:]
    success = None
    
    post = None
    if action in ["qpr", "qnx"]:
        try:
            idx = int(url_key)
            if action == "qpr": idx -= 1
            if action == "qnx": idx += 1
            await query.message.delete()
            await send_queue_item(context.bot, update.effective_chat.id, idx)
        except Exception as e:
            logger.error(f"Error paginating queue: {e}")
        return
        
    post = pending_posts.get(url_key)
    
    if not post:
        try:
            if query.message.photo:
                await query.edit_message_caption(caption="⚠️ Post expired or already processed.", parse_mode='HTML')
            else:
                await query.edit_message_text(text="⚠️ Post expired or already processed.", parse_mode='HTML')
        except Exception as e:
            logger.error(f"Error handling expired post UI: {e}")
        return
        
    img_path = os.path.join(IMAGES_DIR, f"{url_key}.jpg")
    
    if action == "app":
        # Load image bytes from disk if exists
        image_bytes = None
        if os.path.exists(img_path):
            try:
                with open(img_path, "rb") as img_file:
                    image_bytes = img_file.read()
            except Exception as e:
                logger.error(f"Failed to read image {img_path}: {e}")

        success = await asyncio.to_thread(post_tweet, post['generated_tweet'], image_bytes)
        
        if success:
            caption = f"✅ <b>Posted to Twitter!</b>\n\n{post['generated_tweet']}"
            bot_state['posts_published'] += 1
            add_to_history(post['generated_tweet'])
            
            config = load_config()
            interval_sec = get_randomized_interval(config.get("bot", {}))
            bot_state['cooldown_until'] = datetime.now() + timedelta(seconds=interval_sec)
            
            await asyncio.to_thread(mark_posted, post['url'], post['source'])
            del pending_posts[url_key]
            save_pending_posts(pending_posts)
            if os.path.exists(img_path):
                os.remove(img_path)
        else:
            caption = f"⚠️ <b>Failed to post to Twitter! (Check logs/credentials)</b>\n\n{post['generated_tweet']}"
            
    elif action == "rej":
        caption = f"❌ <b>Rejected</b>\n\n{post['generated_tweet']}"
        await asyncio.to_thread(mark_posted, post['url'], post['source'])
        del pending_posts[url_key]
        save_pending_posts(pending_posts)
        
        if os.path.exists(img_path):
            os.remove(img_path)
            
        context.job_queue.run_once(trigger_manual_check, 1)
            
    elif action == "rew":
        await query.answer("Rewriting tweet...")
        new_text = await asyncio.to_thread(generate_tweet_text, post, rewrite=True)
        post['generated_tweet'] = new_text
        pending_posts[url_key] = post
        save_pending_posts(pending_posts)
        
        try:
            await query.message.delete()
        except Exception:
            pass
            
        await send_queue_item(context.bot, update.effective_chat.id, list(pending_posts.keys()).index(url_key))
        return
            
    elif action == "off":
        update_config_value("active", False)
        caption = f"⏸ <b>Bot Paused</b>\n\n{post['generated_tweet']}"
        
    else:
        await query.answer("Unknown action.", show_alert=True)
        return

    reply_markup = None
    if action == "app" and success is False:
        keyboard = [
            [
                InlineKeyboardButton("✅ Retry Approve", callback_data=f"app_{url_key}"),
                InlineKeyboardButton("❌ Reject", callback_data=f"rej_{url_key}")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)

    try:
        if query.message.photo:
            await query.edit_message_caption(caption=caption, parse_mode='HTML', reply_markup=reply_markup)
        else:
            await query.edit_message_text(text=caption, parse_mode='HTML', reply_markup=reply_markup)
    except Exception as e:
        logger.error(f"Error editing message post-action: {e}")

async def handle_menu_buttons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    text = update.message.text
    
    if text == "🔍 Find News":
        await force_check(update, context)
    elif text == "📦 My Queue":
        await show_queue(update, context)
    elif text == "⏯ Pause / Start":
        config = load_config()
        active = config.get("bot", {}).get("active", True)
        update_config_value("active", not active)
        if not active:
            await update.message.reply_text("▶️ <b>Bot Resumed.</b>", parse_mode='HTML')
            context.job_queue.run_once(trigger_manual_check, 1)
        else:
            await update.message.reply_text("⏸ <b>Bot Paused.</b>", parse_mode='HTML')
    elif text == "🤖 Auto-Post: ON/OFF":
        await toggle_auto_post(update, context)
    elif text == "⚙️ Settings":
        keyboard = [
            [InlineKeyboardButton("📝 Edit Prompt", callback_data="set_prompt"), InlineKeyboardButton("⏱ Interval", callback_data="set_interval")],
            [InlineKeyboardButton("🎯 Edit Niche", callback_data="set_niche"), InlineKeyboardButton("🤖 Toggle Mode", callback_data="set_mode")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("⚙️ <b>Settings Panel</b>\nChoose an option to configure or use commands (/add_rss, /remove_rss):", reply_markup=reply_markup, parse_mode='HTML')

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("force", force_check))
    application.add_handler(CommandHandler("parse", force_check))
    application.add_handler(CommandHandler("queue", show_queue))
    application.add_handler(CommandHandler("history", show_history))
    application.add_handler(CommandHandler("set_niche", set_niche))
    application.add_handler(CommandHandler("set_mode", set_mode))
    application.add_handler(CommandHandler("set_tone", set_tone))
    application.add_handler(CommandHandler("set_prompt", set_prompt))
    application.add_handler(CommandHandler("set_interval", set_interval))
    application.add_handler(CommandHandler("set_notify", set_notify))
    application.add_handler(CommandHandler("stop", stop_bot))
    application.add_handler(CommandHandler("noaccept", toggle_auto_post))
    application.add_handler(CommandHandler("add_rss", add_rss))
    application.add_handler(CommandHandler("remove_rss", remove_rss))
    application.add_handler(CommandHandler("add_sub", add_sub))
    application.add_handler(CommandHandler("remove_sub", remove_sub))
    application.add_handler(CommandHandler("clear_sources", clear_sources))
    application.add_handler(CommandHandler("queue", show_queue))
    application.add_handler(CommandHandler("sources", show_sources))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_menu_buttons))

    bot_state['next_run_time'] = datetime.now() + timedelta(seconds=10)
    job_queue = application.job_queue
    job_queue.run_once(scheduled_check, 10)

    logger.info("Starting Telegram Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
