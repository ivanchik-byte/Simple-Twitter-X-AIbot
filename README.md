# Simple AI Twitter Bot

[🇷🇺 Читать на русском](README_ru.md) | [🇬🇧 English](README.md)

An autonomous Python bot for Twitter (X) that researches a niche, picks the best news, generates tweets with LLMs, and posts them. You control everything through a Telegram Bot — approve, reject, or rewrite drafts before they go live.

## Key Features

- **Two-Stage LLM Pipeline:**
  1. **Curation:** Parses RSS feeds and subreddits, filters out ads and spam. The LLM picks the single best post from the batch.
  2. **Generation:** Writes a clean, X-optimized tweet (under 250 characters) — no hashtag spam, just good content.
- **Memory Against Repetition:** Keeps a `post_history.json` log of recent tweets. The LLM gets this context so it never repeats itself.
- **Telegram Dashboard:** Review drafts in a queue. Approve, reject, or hit "Rewrite" for a fresh version — all from Telegram.
- **Scheduling & Cooldowns:**
  - Randomized check intervals (e.g. between 1 and 3 hours) to feel more human.
  - Automatic cooldown after posting to dodge API rate limits and save tokens.
- **Model Agnostic:** Works with any OpenAI-compatible API — OpenAI, Anthropic (via OpenRouter), DeepSeek, or local Ollama.
- **Auto / Manual Modes:** Let the bot discover RSS feeds and subreddits on its own, or give it a strict list to follow.
- **Auto-Post Mode:** Toggle `/noaccept` to go fully autonomous — the bot posts the best news without waiting for your say-so.
- **Bilingual Out of the Box:** Everything — interface and tweets — works in English (`en`) and Russian (`ru`). Switch with `/set_lang`.

---

## Prerequisites

- Python 3.9+
- Twitter Developer Account (Consumer and Access tokens)
- Telegram Bot Token (from BotFather) and your Telegram Chat ID
- An API key from a supported LLM provider (OpenAI, OpenRouter, NVIDIA, DeepSeek, etc.)
- *(Optional)* Google Gemini API Key — used only for parsing images inside news articles.

---

## Installation

1. **Clone the repo:**
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

## Configuration

1. **Environment Variables:**
   Copy the example file:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in your keys:
   - `LLM_API_KEY` — for text generation
   - `GEMINI_API_KEY` — for image parsing (optional)
   - Twitter creds (`TWITTER_CONSUMER_KEY`, etc.)
   - Telegram creds (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)

2. **Bot Settings (`config.yaml`):**
   ```yaml
   bot:
     language: "en"           # "en" or "ru"
     niche: "Artificial Intelligence"
     tone_of_voice: "Expert AI blogger, concise and professional"
     mode: "auto"
     max_length: 280 # Set to 25000 if you have X Premium
     interval: [3600, 10800]  # Random interval between 1h and 3h

   llm:
     base_url: "https://integrate.api.nvidia.com/v1"
     model_name: "deepseek-ai/deepseek-v4-pro"
   ```
   - **Language:** Interface and tweet language.
   - **Max Length:** Max characters for your tweets (280 for free users, up to 25000 for Premium).
   - **Niche & Tone:** What the bot talks about and how it sounds.
   - **Mode:** `auto` (discovers sources) or `manual` (your own list).
   - **LLM:** Set `base_url` and `model_name` (e.g. `https://api.openai.com/v1` and `gpt-4o`).

---

## Telegram Commands & Usage

Start the bot:
```bash
python main.py
```

Open your bot in Telegram and use the inline keyboard or these commands:

- `/start` or `/help` — Show the welcome menu and command list.
- `/status` — Bot health, cooldown timers, stats, and schedule.
- `/parse` (or `/force`) — Force an immediate news search.
- `/queue` — View posts waiting for your approval.
- `/history` — See the last 5 published tweets.
- `/noaccept` — Toggle Auto-Post mode (post without manual approval).
- `/set_lang <en|ru>` — Switch language on the fly.
- `/set_interval <min> [max]` — Set check intervals (e.g. `/set_interval 1h 3h`).
- `/set_niche <name>` — Change the niche.
- `/set_mode <auto|manual>` — Switch between auto-discovery and manual sources.
- `/set_tone <tone>` — Update the writing style.
- `/add_rss <url>` / `/add_sub <name>` — Add custom sources (works in manual mode).

---

## Architecture Notes

- **Async by Design:** LLM calls and RSS parsing run in `asyncio.to_thread` so the Telegram interface stays snappy.
- **SQLite Database:** Uses Write-Ahead Logging (WAL) for safe concurrent access. Tracks published URLs to avoid duplicates.
- **Fail-Safes:** HTML escaping for Telegram limits, smart truncation for X's character limit, automatic backoff on Reddit 429 errors.

## License

MIT License
