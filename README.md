# Simple AI Twitter Bot

[![Python Version](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

[🇷🇺 Читать на русском](README_ru.md) | [🇬🇧 English](README.md)

An autonomous, Python-based Twitter (X) assistant that monitors custom niches, curates high-quality news from RSS feeds and subreddits, drafts engaging posts using Large Language Models (LLMs), and manages publications via an interactive Telegram control panel. 

---

## Table of Contents

- [Key Features](#key-features)
- [Prerequisites](#prerequisites)
- [Installation](#installation)
- [Configuration](#configuration)
  - [Environment Variables](#1-environment-variables)
  - [Bot Config File](#2-bot-settings-configyaml)
- [Telegram Commands](#telegram-commands--usage)
- [Architecture & Internal Design](#architecture-notes)
- [License](#license)

---

## Key Features

- **Two-Stage LLM Pipeline:**
  - **Curation:** Automatically parses RSS feeds and Subreddits, using an LLM to filter out promotional content, sponsored posts, affiliate marketing, and low-quality clickbait. It picks the single most relevant post from the batch.
  - **Generation:** Drafts an X-optimized post of up to a customizable length (max 280 characters for standard users, up to 25,000 for X Premium). Employs natural hooks, paragraph breaks, and excludes hashtag spam.
- **Anti-Repetition Engine:** Logs published posts to `post_history.json` and injects them as negative context into LLM prompts to prevent repetitive topics, phrases, or templates.
- **Telegram Dashboard:** Provides an interactive approval queue with buttons allowing you to approve, reject, or request a complete rewrite from the LLM.
- **Human-like Scheduling:** Supports randomized verification intervals (e.g., check every 1 to 3 hours randomly) to resemble organic human browsing habits.
- **Automatic Cooldowns:** Temporarily suspends checking operations after publishing to conserve API credits and prevent rate-limiting flags.
- **Model Agnostic:** Integrates with any OpenAI-compatible API endpoints (such as OpenAI, Anthropic via OpenRouter, DeepSeek, local Ollama, etc.).
- **Auto & Manual Modes:** Operates either autonomously by discovering sources relevant to your niche or strictly follows a manually declared list of feeds.
- **Autonomous Posting:** Toggle the `/noaccept` mode to bypass manual verification, publishing the best selected news directly on its own schedule.
- **Bilingual Interface:** Supports English (`en`) and Russian (`ru`) out of the box for all menus, buttons, and generated content.

---

## Prerequisites

- Python 3.9 or higher
- A Twitter Developer Account (with Consumer and Access tokens)
- A Telegram Bot Token (via [@BotFather](https://t.me/BotFather)) and your personal Telegram Chat ID
- An API Key for an LLM provider (OpenAI, DeepSeek, OpenRouter, etc.)
- *(Optional)* A Google Gemini API Key (only required for analyzing and summarizing charts/images in news articles)

---

## Installation

1. **Clone the Repository:**
   ```bash
   git clone git@github.com:ivanchik-byte/Simple-Twitter-X-AIbot.git
   cd Simple-Twitter-X-AIbot
   ```

2. **Create and Activate a Virtual Environment:**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

---

## Configuration

### 1. Environment Variables

Copy the template environment file:
```bash
cp .env.example .env
```

Open `.env` and fill in the required keys:
```ini
LLM_API_KEY=your_llm_api_key_here
GEMINI_API_KEY=your_gemini_api_key_here # Optional: For image/chart analysis
TELEGRAM_BOT_TOKEN=your_telegram_bot_token
TELEGRAM_CHAT_ID=your_telegram_chat_id
TWITTER_CONSUMER_KEY=your_twitter_consumer_key
TWITTER_CONSUMER_SECRET=your_twitter_consumer_secret
TWITTER_ACCESS_TOKEN=your_twitter_access_token
TWITTER_ACCESS_TOKEN_SECRET=your_twitter_access_token_secret
TWITTER_BEARER_TOKEN=your_twitter_bearer_token
```

### 2. Bot Settings (`config.yaml`)

Open `config.yaml` to specify the parameters of the bot:
```yaml
bot:
  language: "en"           # Interface language ("en" or "ru")
  niche: "Artificial Intelligence" # Niche topic target
  tone_of_voice: "Expert AI blogger, concise and professional"
  mode: "auto"             # Source mode: "auto" or "manual"
  max_length: 280          # Max tweet characters (use 25000 for X Premium)
  interval: [3600, 10800]  # Checking interval range in seconds (min, max)

llm:
  base_url: "https://integrate.api.nvidia.com/v1"
  model_name: "deepseek-ai/deepseek-v4-pro"
```

---

## Telegram Commands & Usage

Start the bot orchestrator:
```bash
python main.py
```

Open your Telegram chat with the bot. You can use the custom reply keyboard or execute the following slash commands:

| Command | Arguments | Description |
| :--- | :--- | :--- |
| `/start` | | Initializes the bot, showing the main menu keyboard. |
| `/status` | | Shows current status, cooldown timers, niche, and session stats. |
| `/parse` | | Forces an immediate search and analysis of sources. |
| `/queue` | | Opens the interactive approval queue for draft posts. |
| `/history` | | Displays the titles of the last 5 published tweets. |
| `/noaccept` | | Toggles Auto-Post mode (automatic posting without approval). |
| `/set_lang` | `<en\|ru>` | Switches the interface and generation language. |
| `/set_limit` | `<number>` | Sets the maximum tweet character limit (e.g. 280 or 25000). |
| `/set_interval` | `<min> [max]` | Sets checking interval (e.g., `1h 3h` or `2h`). |
| `/set_niche` | `<name>` | Changes the target niche on the fly. |
| `/set_mode` | `<auto\|manual>`| Switches between auto-discovery and manual source lists. |
| `/set_tone` | `<tone>` | Updates the writing style tone of the LLM. |
| `/add_rss` | `<url>` | Adds a custom RSS feed (applies to manual mode). |
| `/remove_rss` | `<url>` | Removes a custom RSS feed. |
| `/add_sub` | `<name>` | Adds a custom subreddit (applies to manual mode). |
| `/remove_sub` | `<name>` | Removes a custom subreddit. |
| `/sources` | | Lists currently used RSS feeds and subreddits. |
| `/clear_sources` | | Clears the cache of auto-discovered sources. |
| `/stop` | | Pauses the scheduled checking cycle. |
| `/help` | | Displays list of available commands and instructions. |

---

## Architecture Notes

- **Asynchronous Execution:** Threaded operations (`asyncio.to_thread`) handle network calls to RSS feeds and LLM endpoints to keep the Telegram polling loop smooth and non-blocking.
- **Robust Database State:** Backed by SQLite running in Write-Ahead Logging (WAL) mode to allow concurrent writes, checking URLs against past posts to prevent duplication.
- **Fail-Safe Integrity:** Automatic HTML sanitization prevents Telegram API crashes. Sentence-aware truncation keeps tweets strictly within boundaries while maintaining readable flows. Implements automatic backoffs to resolve Reddit `429 Too Many Requests` API errors.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
