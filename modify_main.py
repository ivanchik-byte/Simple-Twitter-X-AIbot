import re

with open('main.py', 'r', encoding='utf-8') as f:
    code = f.read()

# Add import
code = re.sub(r'from parser import .*', r'\g<0>\nfrom i18n import t', code)

# get_main_keyboard
code = re.sub(
    r'def get_main_keyboard\(\):.*?return keyboard',
    r'''def get_main_keyboard():
    keyboard = [
        [KeyboardButton(t("btn_find_news")), KeyboardButton(t("btn_queue"))],
        [KeyboardButton(t("btn_pause")), KeyboardButton(t("btn_start"))],
        [KeyboardButton(t("btn_auto_on")), KeyboardButton(t("btn_auto_off"))],
        [KeyboardButton(t("btn_settings"))]
    ]
    return keyboard''',
    code, flags=re.DOTALL
)

# message handler
code = code.replace('if text == "🔍 Find News":', 'if text == t("btn_find_news"):')
code = code.replace('elif text == "📝 Queue":', 'elif text == t("btn_queue"):')
code = code.replace('elif text == "⏸ Pause Bot":', 'elif text == t("btn_pause"):')
code = code.replace('elif text == "▶️ Start Bot":', 'elif text == t("btn_start"):')
code = code.replace('elif text == "⚡ Auto-Post: On":', 'elif text == t("btn_auto_on"):')
code = code.replace('elif text == "⚡ Auto-Post: Off":', 'elif text == t("btn_auto_off"):')
code = code.replace('elif text == "⚙️ Settings":', 'elif text == t("btn_settings"):')

# welcome text
code = re.sub(
    r'welcome_text = f"🤖 <b>Welcome.*?Use the menu below.*?"',
    r'welcome_text = t("msg_welcome", niche=bot_config.get("niche", "N/A"), mode=bot_config.get("mode", "auto"))',
    code, flags=re.DOTALL
)

# help text
code = re.sub(
    r'help_text = "📖 <b>Available Commands:.*?/help - Show this menu"',
    r'help_text = t("msg_help")',
    code, flags=re.DOTALL
)

# Status
code = re.sub(
    r'status_text = f"📊 <b>Bot Status.*?pending_count}"',
    r'''status_text = t("msg_status", niche=niche, last_run=last_run, next_run=next_run, 
                      cd_text=f"\\n💤 Cooldown Until: <code>{cooldown_until}</code>" if cooldown_until != "N/A" else "",
                      published=published, pending=pending_count)''',
    code, flags=re.DOTALL
)

# Other specific replaces
code = code.replace('await update.message.reply_text("🔄 Forcing an immediate news check. This might take a minute...")',
                    'await update.message.reply_text(t("msg_forcing"))')
code = code.replace('await update.message.reply_text("⏸ <b>Bot Paused.</b> News checking suspended.", parse_mode=\'HTML\')',
                    'await update.message.reply_text(t("msg_bot_paused_main"), parse_mode=\'HTML\')')
code = code.replace('await update.message.reply_text("✅ <b>Auto Post: ON</b> (No approval required)", parse_mode=\'HTML\')',
                    'await update.message.reply_text(t("msg_auto_on"), parse_mode=\'HTML\')')
code = code.replace('await update.message.reply_text("❌ <b>Auto Post: OFF</b> (Manual approval required)", parse_mode=\'HTML\')',
                    'await update.message.reply_text(t("msg_auto_off"), parse_mode=\'HTML\')')
code = code.replace('await bot.send_message(chat_id=chat_id, text="📭 Post queue is empty.")',
                    'await bot.send_message(chat_id=chat_id, text=t("msg_empty_queue"))')

code = code.replace('InlineKeyboardButton("✅ Approve", callback_data=f"app_{url_key}")',
                    'InlineKeyboardButton(t("btn_approve"), callback_data=f"app_{url_key}")')
code = code.replace('InlineKeyboardButton("❌ Reject", callback_data=f"rej_{url_key}")',
                    'InlineKeyboardButton(t("btn_reject"), callback_data=f"rej_{url_key}")')
code = code.replace('InlineKeyboardButton("🔄 Rewrite", callback_data=f"rew_{url_key}")',
                    'InlineKeyboardButton(t("btn_rewrite"), callback_data=f"rew_{url_key}")')
code = code.replace('InlineKeyboardButton("⏸ Turn Off", callback_data=f"off_{url_key}")',
                    'InlineKeyboardButton(t("btn_turn_off"), callback_data=f"off_{url_key}")')
code = code.replace('InlineKeyboardButton("⬅️ Prev", callback_data=f"qpr_{index}")',
                    'InlineKeyboardButton(t("btn_prev"), callback_data=f"qpr_{index}")')
code = code.replace('InlineKeyboardButton("Next ➡️", callback_data=f"qnx_{index}")',
                    'InlineKeyboardButton(t("btn_next"), callback_data=f"qnx_{index}")')
code = code.replace('InlineKeyboardButton("✅ Retry Approve", callback_data=f"app_{url_key}")',
                    'InlineKeyboardButton(t("btn_retry"), callback_data=f"app_{url_key}")')

code = re.sub(r'message_text = f"📰 <b>Queued Post:</b>\\n\{safe_title\}\\n\\n📝 <b>Generated Tweet:</b>\\n\{safe_tweet\}"',
              r'message_text = t("msg_queued_post", title=safe_title, tweet=safe_tweet)', code)
code = re.sub(r'message_text = f"📰 <b>New Post:</b>\\n\{safe_title\}\\n\\n📝 <b>Generated Tweet:</b>\\n\{safe_tweet\}"',
              r'message_text = t("msg_new_post", title=safe_title, tweet=safe_tweet)', code)

code = code.replace('await update.message.reply_text("📭 Post history is empty.")',
                    'await update.message.reply_text(t("msg_empty_history"))')
code = re.sub(r'text = "📜 <b>Last 5 Published Posts:</b>\\n\\n"', r'text = t("msg_history_header")', code)
code = code.replace('await context.bot.send_message(chat_id=chat_id, text="ℹ️ No new unposted news found.")',
                    'await context.bot.send_message(chat_id=chat_id, text=t("msg_no_news"))')

code = re.sub(r'text=f"✅ <b>Automatically Posted:</b>\\n\{safe_title\}\\n\\n\{safe_tweet\}"',
              r'text=t("msg_auto_posted", title=safe_title, tweet=safe_tweet)', code)
code = re.sub(r'text=f"⚠️ <b>Auto Post Failed:</b>\\n\{safe_title\}"',
              r'text=t("msg_auto_failed", title=safe_title)', code)

code = re.sub(r'await update\.message\.reply_text\(f"✅ <b>Posted to Twitter!</b>\\n\\n\{safe_tweet\}".*?\)',
              r'await update.message.reply_text(t("msg_posted", tweet=safe_tweet), parse_mode="HTML")', code)
code = re.sub(r'await update\.message\.reply_text\(f"⚠️ <b>Failed to post to Twitter! \(Check logs/credentials\)</b>\\n\\n\{safe_tweet\}".*?\)',
              r'await update.message.reply_text(t("msg_post_failed", tweet=safe_tweet), parse_mode="HTML")', code)

code = re.sub(r'await update\.message\.reply_text\(f"❌ <b>Rejected</b>\\n\\n\{safe_tweet\}".*?\)',
              r'await update.message.reply_text(t("msg_rejected", tweet=safe_tweet), parse_mode="HTML")', code)
code = re.sub(r'await update\.message\.reply_text\(f"⏸ <b>Bot Paused</b>\\n\\n\{safe_tweet\}".*?\)',
              r'await update.message.reply_text(t("msg_paused", tweet=safe_tweet), parse_mode="HTML")', code)

code = code.replace('await update.message.reply_text("▶️ <b>Bot Resumed.</b>", parse_mode=\'HTML\')',
                    'await update.message.reply_text(t("msg_bot_resumed"), parse_mode=\'HTML\')')
code = code.replace('await update.message.reply_text("⏸ <b>Bot Paused.</b>", parse_mode=\'HTML\')',
                    'await update.message.reply_text(t("msg_bot_paused_main"), parse_mode=\'HTML\')')

code = code.replace('await query.answer("Rewriting tweet...")', 'await query.answer(t("msg_rewriting"))')

# add /set_lang command
set_lang_code = '''
async def cmd_set_lang(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not is_authorized(update):
        return
    if len(context.args) != 1 or context.args[0].lower() not in ["en", "ru"]:
        await update.message.reply_text("Usage: <code>/set_lang &lt;en|ru&gt;</code>", parse_mode='HTML')
        return
        
    lang = context.args[0].lower()
    config = load_config()
    if 'bot' not in config:
        config['bot'] = {}
    config['bot']['language'] = lang
    save_config(config)
    
    await update.message.reply_text(f"✅ Language updated to {lang.upper()}\\nSend /start to update keyboard.", parse_mode='HTML')
'''
code = code.replace('async def cmd_set_niche(', set_lang_code + '\nasync def cmd_set_niche(')
code = code.replace('app.add_handler(CommandHandler("set_niche", cmd_set_niche))',
                    'app.add_handler(CommandHandler("set_lang", cmd_set_lang))\n    app.add_handler(CommandHandler("set_niche", cmd_set_niche))')

with open('main.py', 'w', encoding='utf-8') as f:
    f.write(code)
