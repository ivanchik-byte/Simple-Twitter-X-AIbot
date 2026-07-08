# Simple AI Twitter Bot

An autonomous Python-based Twitter (X) bot that researches a specific niche, curates the best news, generates highly engaging tweets using Large Language Models, and publishes them. It acts as an elite ghostwriter, controllable entirely via a Telegram Bot interface.

## 🔥 Key Features

- **🧠 Two-Stage LLM Pipeline:**
  1. **Curation:** Parses dozens of RSS feeds and subreddits, filtering out ads, affiliate spam, and course-selling garbage. The LLM acts as an editor-in-chief, selecting only the SINGLE most viral and interesting post.
  2. **Generation:** Writes a punchy, X-optimized tweet (under 250 chars) with hooks, proper formatting, and zero cliché hashtags. 
- **🤖 Anti-Repetition Memory:** Maintains a `post_history.json` of the last published tweets and injects them into the LLM prompt. The bot *will not* repeat the same topics or phrases day after day.
- **📱 Telegram Control Panel:** Manage everything from Telegram. Review posts via a Queue system, approve/reject them, or click "Rewrite" to instantly get a fresh take if you don't like the drafted tweet.
- **🕒 Human-Like Scheduling & Cooldowns:** 
  - Set randomized intervals (e.g., `/set_interval 1h 3h`). The bot will pick a random time between 1 and 3 hours to mimic organic human activity.
  - After posting, the bot enters a strict **Standby/Cooldown mode** where it pauses all parsing to avoid API rate limits and save LLM tokens.
- **⚡ Bring Your Own AI:** Compatible with any OpenAI-compatible API (OpenAI, Anthropic via OpenRouter, DeepSeek, or local Ollama instances).
- **⚙️ Auto / Manual Modes:** Let the bot automatically discover RSS feeds and subreddits based on your Niche, or manually define your own strict list of sources.
- **🚀 Auto-Post Mode:** Tired of manual approval? Toggle `/noaccept` to let the bot run fully autonomously, publishing the best news on its own schedule.

---

## 🛠 Prerequisites

- Python 3.9+
- Twitter Developer Account (Consumer & Access tokens)
- Telegram Bot Token (via BotFather) & your personal Telegram Chat ID
- An API key from your preferred LLM provider (e.g., OpenAI, OpenRouter, NVIDIA, DeepSeek)
- *(Optional)* Google Gemini API Key: Used purely for reading and understanding charts/images if they appear in news articles.

---

## 🚀 Installation

1. **Clone the repository:**
   ```bash
   git clone git@github.com:ivanchik-byte/Simple-Twitter-X-AIbot.git
   cd Simple-Twitter-X-AIbot
   ```

2. **Create a virtual environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## ⚙️ Configuration

1. **Environment Variables:**
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in:
   - `LLM_API_KEY`: Your key for text generation.
   - `GEMINI_API_KEY`: Your key for Gemini (for image parsing).
   - Twitter credentials (`TWITTER_CONSUMER_KEY`, etc.)
   - Telegram credentials (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)

2. **Bot Settings (`config.yaml`):**
   ```yaml
   bot:
     niche: "Artificial Intelligence"
     tone_of_voice: "Expert AI blogger, concise and professional"
     mode: "auto"
     interval: [3600, 10800] # Random interval between 1h and 3h

   llm:
     base_url: "https://integrate.api.nvidia.com/v1"
     model_name: "deepseek-ai/deepseek-v4-pro"
   ```
   - **Niche & Tone:** Define what the bot writes about and how it sounds.
   - **Mode:** `auto` (auto-discovers sources) or `manual` (uses your defined sources).
   - **LLM:** Set your `base_url` and `model_name` (e.g., `https://api.openai.com/v1` and `gpt-4o`).

---

## 🎮 Telegram Commands & Usage

Start the bot:
```bash
python main.py
```

Open your Telegram bot. You can use the built-in keyboard menu or the following commands:

- `/start` or `/help` - Show the welcome menu and list of all commands.
- `/status` - View bot health, cooldown timers, published stats, and schedule.
- `/parse` (or `/force`) - Force an immediate search for breaking news.
- `/queue` - View pending posts waiting for your approval.
- `/history` - View the last 5 published tweets to see what the bot remembers.
- `/noaccept` - Toggle Auto-Post mode (publish without manual approval).
- `/set_interval <min> [max]` - Set checking intervals (e.g., `/set_interval 1h 3h`).
- `/set_niche <name>` - Change the bot's target niche on the fly.
- `/set_mode <auto|manual>` - Switch between automatic source discovery and manual sources.
- `/set_tone <tone>` - Update the ghostwriter's tone of voice.
- `/add_rss <url>` / `/add_sub <name>` - Add custom sources (for manual mode).

---

## 🏗 Architecture Notes

- **Asynchronous & Thread-Safe:** LLM network calls and RSS parsing are wrapped in `asyncio.to_thread` to keep the Telegram polling interface instantly responsive.
- **SQLite WAL:** The database tracks published URLs (to avoid duplicates) and uses Write-Ahead Logging for safe concurrent access.
- **Fail-Safes:** Implements smart HTML escaping for Telegram limits, X (Twitter) character limit truncation (with sentence awareness), and Reddit 429 Rate Limit backoffs.

## 📄 License
MIT License
