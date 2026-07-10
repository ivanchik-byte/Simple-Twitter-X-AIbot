# Simple AI Twitter Bot

[🇷🇺 Читать на русском](README_ru.md) | [🇬🇧 English](README.md)

An autonomous Python-based Twitter (X) bot that researches a specific niche, curates relevant news, generates tweets using Large Language Models (LLMs), and publishes them. The bot is managed entirely through a Telegram Bot interface, offering a queue system and manual approval workflows.

## Key Features

- **Two-Stage LLM Pipeline:**
  1. **Curation:** Parses RSS feeds and subreddits, filtering out advertisements, affiliate links, and self-promotion. The LLM selects the single most engaging post from the batch.
  2. **Generation:** Drafts an X-optimized tweet (under 250 characters) formatted appropriately without hashtags.
- **Anti-Repetition Memory:** Maintains a `post_history.json` log of recently published tweets. This history is injected into the LLM prompt to prevent the bot from repeating topics or phrases.
- **Telegram Control Panel:** Review drafted posts via a queue system. Users can approve, reject, or request a complete rewrite of the tweet directly from the Telegram interface.
- **Scheduling & Cooldowns:** 
  - Supports randomized checking intervals (e.g., between 1 and 3 hours) to mimic organic user activity.
  - Implements a strict standby/cooldown mode after publishing to avoid API rate limits and conserve LLM tokens.
- **Model Agnostic:** Compatible with any OpenAI-compatible API, including OpenAI, Anthropic (via OpenRouter), DeepSeek, or local Ollama instances.
- **Auto / Manual Modes:** Can automatically discover RSS feeds and subreddits based on a defined niche, or strictly follow a manually defined list of sources.
- **Auto-Post Mode:** Includes an autonomous mode (`/noaccept`) that bypasses the manual approval queue and publishes the best news on its own schedule.
- **Bilingual Support:** Interfaces and tweet generation fully support English (`en`) and Russian (`ru`). Set language via `/set_lang` or config.

---

## Prerequisites

- Python 3.9+
- Twitter Developer Account (Consumer and Access tokens)
- Telegram Bot Token (via BotFather) and your Telegram Chat ID
- An API key from a supported LLM provider (OpenAI, OpenRouter, NVIDIA, DeepSeek, etc.)
- *(Optional)* Google Gemini API Key: Utilized solely for reading and analyzing charts/images within news articles.

---

## Installation

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

## Configuration

1. **Environment Variables:**
   Copy the example environment file:
   ```bash
   cp .env.example .env
   ```
   Open `.env` and fill in the required credentials:
   - `LLM_API_KEY`: API key for text generation.
   - `GEMINI_API_KEY`: API key for Gemini (required for image parsing).
   - Twitter credentials (`TWITTER_CONSUMER_KEY`, etc.)
   - Telegram credentials (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)

2. **Bot Settings (`config.yaml`):**
   ```yaml
   bot:
     language: "en" # "en" or "ru"
     niche: "Artificial Intelligence"
     tone_of_voice: "Expert AI blogger, concise and professional"
     mode: "auto"
     interval: [3600, 10800] # Random interval between 1h and 3h

   llm:
     base_url: "https://integrate.api.nvidia.com/v1"
     model_name: "deepseek-ai/deepseek-v4-pro"
   ```
   - **Language:** Interface and tweet language.
   - **Niche & Tone:** Define the content focus and writing style.
   - **Mode:** `auto` (auto-discovers sources) or `manual` (uses defined sources).
   - **LLM:** Configure the endpoint by setting `base_url` and `model_name` (e.g., `https://api.openai.com/v1` and `gpt-4o`).

---

## Telegram Commands & Usage

Start the application:
```bash
python main.py
```

Once running, interact with the bot via Telegram using the built-in keyboard menu or the following commands:

- `/start` or `/help` - Display the welcome menu and command list.
- `/status` - View bot health, cooldown timers, published statistics, and schedule.
- `/parse` (or `/force`) - Force an immediate search for news.
- `/queue` - View pending posts awaiting approval.
- `/history` - View the last 5 published tweets.
- `/noaccept` - Toggle Auto-Post mode (publish without manual approval).
- `/set_lang <en|ru>` - Switch the bot's language.
- `/set_interval <min> [max]` - Set checking intervals (e.g., `/set_interval 1h 3h`).
- `/set_niche <name>` - Update the target niche.
- `/set_mode <auto|manual>` - Switch between automatic source discovery and manual sources.
- `/set_tone <tone>` - Update the writing tone.
- `/add_rss <url>` / `/add_sub <name>` - Add custom sources (effective in manual mode).

---

## Architecture Notes

- **Asynchronous Execution:** LLM network calls and RSS parsing utilize `asyncio.to_thread` to maintain a responsive Telegram polling interface.
- **SQLite Database:** Utilizes Write-Ahead Logging (WAL) for safe concurrent access, primarily tracking published URLs to prevent duplicates.
- **Fail-Safes:** Includes HTML escaping to comply with Telegram parsing limits, precise text truncation for X (Twitter) character limits, and automatic backoffs for Reddit 429 Rate Limits.

## License

MIT License
