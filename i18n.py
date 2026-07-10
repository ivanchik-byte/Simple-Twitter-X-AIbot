import json
from config import load_config

def get_lang() -> str:
    config = load_config()
    return config.get("bot", {}).get("language", "en")

TEXTS = {
    "en": {
        "btn_find_news": "🔍 Find News",
        "btn_queue": "📝 Queue",
        "btn_pause": "⏸ Pause Bot",
        "btn_start": "▶️ Start Bot",
        "btn_auto_on": "⚡ Auto-Post: On",
        "btn_auto_off": "⚡ Auto-Post: Off",
        "btn_settings": "⚙️ Settings",
        
        "btn_approve": "✅ Approve",
        "btn_reject": "❌ Reject",
        "btn_rewrite": "🔄 Rewrite",
        "btn_turn_off": "⏸ Turn Off",
        "btn_retry": "✅ Retry Approve",
        "btn_prev": "⬅️ Prev",
        "btn_next": "Next ➡️",
        
        "msg_welcome": "🤖 <b>Welcome to AI Twitter Bot Control Panel</b>\n\n🎯 Current Niche: <code>{niche}</code>\n⚙️ Operating Mode: <code>{mode}</code>\n\nUse the menu below to control the bot. Type /help to see all commands.",
        "msg_help": "📖 <b>Available Commands:</b>\n/status - View bot health and schedule\n/parse (or /force) - Force an immediate news check\n/queue - Show pending posts\n/history - Show last published posts\n/sources - Show current RSS/Reddit sources\n/set_lang &lt;en|ru&gt; - Set bot language\n/set_niche &lt;name&gt; - Change niche\n/set_mode &lt;auto|manual&gt; - Change mode\n/set_tone &lt;tone&gt; - Change tone of voice\n/set_prompt &lt;text&gt; - Set custom LLM instructions\n/set_interval &lt;min&gt; [max] - Set post interval (e.g. 1h 3h)\n/set_notify &lt;time&gt; - Set notify before post (e.g. 1h, 0)\n/add_rss &lt;url&gt; - Add RSS feed (manual mode)\n/remove_rss &lt;url&gt; - Remove RSS feed\n/add_sub &lt;name&gt; - Add subreddit (manual mode)\n/remove_sub &lt;name&gt; - Remove subreddit (manual mode)\n/clear_sources - Clear discovered sources cache\n/stop - Pause the bot\n/noaccept - Toggle Auto Post mode\n/help - Show this menu",
        
        "msg_status": "📊 <b>Bot Status</b>\n\n🎯 Niche: <code>{niche}</code>\n🕒 Last Check: <code>{last_run}</code>\n⏳ Next Check: <code>{next_run}</code>{cd_text}\n✅ Posts Published (this session): <code>{published}</code>\n📦 Pending Approvals: <code>{pending}</code>",
        "msg_cooldown": "\n💤 Cooldown Until: <code>{cd}</code>",
        
        "msg_empty_queue": "📭 Post queue is empty.",
        "msg_empty_history": "📭 Post history is empty.",
        "msg_history_header": "📜 <b>Last 5 Published Posts:</b>\n\n",
        
        "msg_queued_post": "📰 <b>Queued Post:</b>\n{title}\n\n📝 <b>Generated Tweet:</b>\n{tweet}",
        "msg_new_post": "📰 <b>New Post:</b>\n{title}\n\n📝 <b>Generated Tweet:</b>\n{tweet}",
        
        "msg_auto_posted": "✅ <b>Automatically Posted:</b>\n{title}\n\n{tweet}",
        "msg_auto_failed": "⚠️ <b>Auto Post Failed:</b>\n{title}",
        
        "msg_posted": "✅ <b>Posted to Twitter!</b>\n\n{tweet}",
        "msg_post_failed": "⚠️ <b>Failed to post to Twitter! (Check logs/credentials)</b>\n\n{tweet}",
        "msg_rejected": "❌ <b>Rejected</b>\n\n{tweet}",
        "msg_paused": "⏸ <b>Bot Paused</b>\n\n{tweet}",
        "msg_bot_resumed": "▶️ <b>Bot Resumed.</b>",
        "msg_bot_paused_main": "⏸ <b>Bot Paused.</b> News checking suspended.",
        
        "msg_rewriting": "Rewriting tweet...",
        "msg_no_news": "ℹ️ No new unposted news found.",
        "msg_forcing": "🔄 Forcing an immediate news check. This might take a minute...",
        
        "msg_auto_on": "✅ <b>Auto Post: ON</b> (No approval required)",
        "msg_auto_off": "❌ <b>Auto Post: OFF</b> (Manual approval required)"
    },
    "ru": {
        "btn_find_news": "🔍 Найти новости",
        "btn_queue": "📝 Очередь",
        "btn_pause": "⏸ Пауза",
        "btn_start": "▶️ Запустить",
        "btn_auto_on": "⚡ Авто-пост: Вкл",
        "btn_auto_off": "⚡ Авто-пост: Выкл",
        "btn_settings": "⚙️ Настройки",
        
        "btn_approve": "✅ Одобрить",
        "btn_reject": "❌ Отклонить",
        "btn_rewrite": "🔄 Переписать",
        "btn_turn_off": "⏸ Выключить",
        "btn_retry": "✅ Повторить отправку",
        "btn_prev": "⬅️ Назад",
        "btn_next": "Вперед ➡️",
        
        "msg_welcome": "🤖 <b>Панель управления AI Twitter Bot</b>\n\n🎯 Текущая ниша: <code>{niche}</code>\n⚙️ Режим работы: <code>{mode}</code>\n\nИспользуй меню ниже для управления. Введи /help чтобы увидеть все команды.",
        "msg_help": "📖 <b>Доступные команды:</b>\n/status - Показать статус бота и расписание\n/parse (или /force) - Принудительно запустить поиск новостей\n/queue - Показать очередь постов\n/history - Показать последние опубликованные посты\n/sources - Показать текущие источники RSS/Reddit\n/set_lang &lt;en|ru&gt; - Изменить язык бота\n/set_niche &lt;название&gt; - Изменить нишу\n/set_mode &lt;auto|manual&gt; - Изменить режим\n/set_tone &lt;тон&gt; - Изменить тон постов\n/set_prompt &lt;текст&gt; - Задать кастомный промпт LLM\n/set_interval &lt;мин&gt; [макс] - Задать интервал постинга (напр. 1h 3h)\n/set_notify &lt;время&gt; - Уведомление до постинга (напр. 1h, 0)\n/add_rss &lt;url&gt; - Добавить RSS (ручной режим)\n/remove_rss &lt;url&gt; - Удалить RSS\n/add_sub &lt;имя&gt; - Добавить сабреддит (ручной режим)\n/remove_sub &lt;имя&gt; - Удалить сабреддит (ручной режим)\n/clear_sources - Очистить кэш найденных источников\n/stop - Поставить бота на паузу\n/noaccept - Вкл/Выкл режим Авто-постинга\n/help - Показать это меню",
        
        "msg_status": "📊 <b>Статус Бота</b>\n\n🎯 Ниша: <code>{niche}</code>\n🕒 Последняя проверка: <code>{last_run}</code>\n⏳ Следующая: <code>{next_run}</code>{cd_text}\n✅ Постов опубликовано (за сессию): <code>{published}</code>\n📦 Ожидает проверки: <code>{pending}</code>",
        "msg_cooldown": "\n💤 Кулдаун до: <code>{cd}</code>",
        
        "msg_empty_queue": "📭 Очередь постов пуста.",
        "msg_empty_history": "📭 История постов пуста.",
        "msg_history_header": "📜 <b>Последние 5 постов:</b>\n\n",
        
        "msg_queued_post": "📰 <b>Пост в очереди:</b>\n{title}\n\n📝 <b>Сгенерированный твит:</b>\n{tweet}",
        "msg_new_post": "📰 <b>Новый пост:</b>\n{title}\n\n📝 <b>Сгенерированный твит:</b>\n{tweet}",
        
        "msg_auto_posted": "✅ <b>Опубликовано автоматически:</b>\n{title}\n\n{tweet}",
        "msg_auto_failed": "⚠️ <b>Ошибка авто-публикации:</b>\n{title}",
        
        "msg_posted": "✅ <b>Опубликовано в Twitter!</b>\n\n{tweet}",
        "msg_post_failed": "⚠️ <b>Ошибка при публикации в Twitter! (Проверь логи/ключи)</b>\n\n{tweet}",
        "msg_rejected": "❌ <b>Отклонено</b>\n\n{tweet}",
        "msg_paused": "⏸ <b>Бот поставлен на паузу</b>\n\n{tweet}",
        "msg_bot_resumed": "▶️ <b>Работа бота возобновлена.</b>",
        "msg_bot_paused_main": "⏸ <b>Бот на паузе.</b> Проверка новостей приостановлена.",
        
        "msg_rewriting": "Переписываю твит...",
        "msg_no_news": "ℹ️ Новых неопубликованных новостей не найдено.",
        "msg_forcing": "🔄 Принудительный поиск новостей. Это займет около минуты...",
        
        "msg_auto_on": "✅ <b>Авто-пост: ВКЛ</b> (Подтверждение не требуется)",
        "msg_auto_off": "❌ <b>Авто-пост: ВЫКЛ</b> (Требуется ручное подтверждение)"
    }
}

def t(key: str, **kwargs) -> str:
    lang = get_lang()
    if lang not in TEXTS:
        lang = "en"
    text = TEXTS[lang].get(key, key)
    if kwargs:
        try:
            text = text.format(**kwargs)
        except KeyError:
            pass
    return text
