import os
import logging
import random
import json
import hashlib
import asyncio
import yaml
from datetime import datetime, timedelta
from dotenv import load_dotenv
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes
from io import BytesIO

load_dotenv()

from parser import get_new_posts, mark_posted
from media_manager import process_media
from llm_client import generate_tweet_text
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
    "posts_published": 0
}

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
        
    config = load_config()
    niche = config.get("bot", {}).get("niche", "Unknown")
    mode = config.get("bot", {}).get("mode", "Unknown")
    
    welcome_text = (
        "🤖 <b>Welcome to AI Twitter Bot Control Panel</b>\n\n"
        f"🎯 Current Niche: <code>{niche}</code>\n"
        f"⚙️ Operating Mode: <code>{mode}</code>\n\n"
        "Available Commands:\n"
        "/status - View bot health and schedule\n"
        "/parse (or /force) - Force an immediate news check\n"
        "/queue - Show pending posts\n"
        "/sources - Show current RSS/Reddit sources\n"
        "/set_niche &lt;name&gt; - Change niche\n"
        "/set_mode &lt;auto|manual&gt; - Change mode\n"
        "/set_tone &lt;tone&gt; - Change tone of voice\n"
        "/clear_sources - Clear discovered sources cache\n"
        "/help - Show this menu"
    )
    await update.message.reply_text(welcome_text, parse_mode='HTML')

async def status(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        return
        
    config = load_config()
    niche = config.get("bot", {}).get("niche", "Unknown")
    
    last_run = bot_state['last_run_time'].strftime("%Y-%m-%d %H:%M:%S") if bot_state['last_run_time'] else "Never"
    next_run = bot_state['next_run_time'].strftime("%Y-%m-%d %H:%M:%S") if bot_state['next_run_time'] else "Not scheduled"
    
    text = (
        "📊 <b>Bot Status</b>\n\n"
        f"🎯 Niche: <code>{niche}</code>\n"
        f"🕒 Last Check: <code>{last_run}</code>\n"
        f"⏳ Next Check: <code>{next_run}</code>\n"
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
        await update.message.reply_text(f"✅ Обновлено: `{key}` = `{value}`", parse_mode='Markdown')
    except Exception as e:
        logger.error(f"Error updating config: {e}")
        await update.message.reply_text(f"❌ Ошибка обновления: {e}")

async def set_niche(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: `/set_niche <название>`", parse_mode='Markdown')
        return
    await update_config(update, "niche", " ".join(context.args))

async def set_mode(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args or context.args[0] not in ['auto', 'manual']:
        await update.message.reply_text("Использование: `/set_mode auto` или `/set_mode manual`", parse_mode='Markdown')
        return
    await update_config(update, "mode", context.args[0])

async def set_tone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not context.args:
        await update.message.reply_text("Использование: `/set_tone <описание>`", parse_mode='Markdown')
        return
    await update_config(update, "tone_of_voice", " ".join(context.args))

async def clear_sources(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    if os.path.exists("auto_sources.json"):
        os.remove("auto_sources.json")
        await update.message.reply_text("✅ Файл `auto_sources.json` удален. Бот найдет новые источники при следующем парсинге.", parse_mode='Markdown')
    else:
        await update.message.reply_text("ℹ️ Кэш источников пуст.", parse_mode='Markdown')

async def show_queue(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update): return
    if not pending_posts:
        await update.message.reply_text("📭 Очередь постов пуста.")
        return
        
    text = "📦 *Очередь постов:*\n\n"
    for idx, (key, post) in enumerate(pending_posts.items(), 1):
        text += f"{idx}. {post.get('title', 'Без заголовка')}\n"
    await update.message.reply_text(text, parse_mode='Markdown')

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
            except:
                pass
    else:
        sources = config.get("sources", {})
        
    text = f"🔍 *Источники ({mode.upper()}):*\n\n"
    text += "*RSS:*\n" + ("\n".join(f"- {s}" for s in sources.get("rss", [])) or "Нет") + "\n\n"
    text += "*Subreddits:*\n" + ("\n".join(f"- {s}" for s in sources.get("subreddits", [])) or "Нет")
    
    await update.message.reply_text(text, parse_mode='Markdown')

async def scheduled_check(context: ContextTypes.DEFAULT_TYPE):
    await check_news(context, manual=False)

async def check_news(context: ContextTypes.DEFAULT_TYPE, manual=False):
    chat_id = os.getenv("TELEGRAM_CHAT_ID")
    if not chat_id:
        logger.error("TELEGRAM_CHAT_ID is not set! Please set it in .env")
        return

    logger.info("Checking for new posts...")
    bot_state['last_run_time'] = datetime.now()
    
    try:
        posts = await asyncio.to_thread(get_new_posts)
        found_any = False
        
        for post in posts:
            found_any = True
            logger.info(f"Processing post: {post['title']}")
            
            post = await asyncio.to_thread(process_media, post)
            tweet_text = await asyncio.to_thread(generate_tweet_text, post)
            post['generated_tweet'] = tweet_text
            
            url_key = hashlib.sha256(post['url'].encode()).hexdigest()[:16]
            
            # Save image to disk to survive restarts
            if post.get('final_image_bytes'):
                try:
                    img_path = os.path.join(IMAGES_DIR, f"{url_key}.jpg")
                    with open(img_path, "wb") as img_file:
                        img_file.write(post['final_image_bytes'])
                except Exception as e:
                    logger.error(f"Failed to save image for {url_key}: {e}")
            
            post_for_json = post.copy()
            if 'final_image_bytes' in post_for_json:
                del post_for_json['final_image_bytes']
            
            pending_posts[url_key] = post_for_json
            save_pending_posts(pending_posts)
            
            keyboard = [
                [
                    InlineKeyboardButton("✅ Approve", callback_data=f"app_{url_key}"),
                    InlineKeyboardButton("❌ Reject", callback_data=f"rej_{url_key}")
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            message_text = f"📰 <b>New Post:</b>\n{post['title']}\n\n📝 <b>Generated Tweet:</b>\n{tweet_text}"
            
            # Use the bytes in memory for sending to TG, then we drop them
            if post.get('final_image_bytes'):
                await context.bot.send_photo(
                    chat_id=chat_id,
                    photo=BytesIO(post['final_image_bytes']),
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
                
        if manual and not found_any:
            await context.bot.send_message(chat_id=chat_id, text="ℹ️ No new unposted news found.")
            
    except Exception as e:
        logger.error(f"Error during check_news: {e}")
        if manual:
            await context.bot.send_message(chat_id=chat_id, text=f"⚠️ Error occurred: {e}")

    if not manual:
        interval = random.randint(5 * 3600, 8 * 3600)
        logger.info(f"Next check scheduled in {interval/3600:.2f} hours.")
        bot_state['next_run_time'] = datetime.now() + timedelta(seconds=interval)
        context.job_queue.run_once(scheduled_check, interval)

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_admin(update):
        await update.callback_query.answer("⛔ Unauthorized.", show_alert=True)
        return
        
    query = update.callback_query
    await query.answer()
    
    data = query.data
    
    if len(data) < 5 or data[3] != '_':
        await query.answer("Invalid action data format.", show_alert=True)
        return
        
    action = data[:3]
    url_key = data[4:]
    success = None
    
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

def main():
    token = os.getenv("TELEGRAM_BOT_TOKEN")
    if not token:
        logger.error("TELEGRAM_BOT_TOKEN not set!")
        return

    application = ApplicationBuilder().token(token).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("help", start))
    application.add_handler(CommandHandler("status", status))
    application.add_handler(CommandHandler("force", force_check))
    application.add_handler(CommandHandler("parse", force_check))
    application.add_handler(CommandHandler("set_niche", set_niche))
    application.add_handler(CommandHandler("set_mode", set_mode))
    application.add_handler(CommandHandler("set_tone", set_tone))
    application.add_handler(CommandHandler("clear_sources", clear_sources))
    application.add_handler(CommandHandler("queue", show_queue))
    application.add_handler(CommandHandler("sources", show_sources))
    application.add_handler(CallbackQueryHandler(button_handler))

    bot_state['next_run_time'] = datetime.now() + timedelta(seconds=10)
    job_queue = application.job_queue
    job_queue.run_once(scheduled_check, 10)

    logger.info("Starting Telegram Bot...")
    application.run_polling()

if __name__ == '__main__':
    main()
