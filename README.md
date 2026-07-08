# Simple Twitter AI Bot

An autonomous Python-based Twitter (X) bot that researches a specific niche, generates engaging tweets using large language models, and publishes them based on user approval via Telegram.

## Features

- **Autonomous Research**: Automatically discovers the best RSS feeds and subreddits for your chosen niche.
- **Bring Your Own AI**: Compatible with any OpenAI-compatible API (OpenAI, Anthropic via OpenRouter, DeepSeek, or local Ollama instances).
- **Telegram Control Panel**: Review, approve, or reject generated tweets directly from Telegram before they are published.
- **State Persistence**: Uses SQLite and local caching to ensure pending posts survive server restarts without data loss.
- **Human-like Scheduling**: Randomizes checking intervals to mimic organic human activity on Twitter.

## Prerequisites

- Python 3.9 or higher
- A Twitter Developer account (with Consumer and Access tokens)
- A Telegram Bot token (via BotFather) and your personal Telegram Chat ID
- An API key from your preferred LLM provider (e.g., OpenAI, OpenRouter, NVIDIA)
- A Google Gemini API Key (specifically used for understanding charts/images if they appear in news articles)

## Installation

1. Clone the repository:
   ```bash
   git clone git@github.com:ivanchik-byte/Simple-Twitter-AIbot.git
   cd Simple-Twitter-AIbot
   ```

2. Create a virtual environment and activate it:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows use: venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Configuration

1. **Environment Variables**:
   Copy the example environment file and fill in your actual API keys.
   ```bash
   cp .env.example .env
   ```
   Open `.env` in your text editor. Crucial variables:
   - `LLM_API_KEY`: Your key for text generation (e.g. OpenAI, DeepSeek, etc.)
   - `GEMINI_API_KEY`: Your key for Google Gemini (required for generating descriptions for charts/images).
   - Twitter credentials (`TWITTER_CONSUMER_KEY`, etc.)
   - Telegram credentials (`TELEGRAM_BOT_TOKEN`, `TELEGRAM_CHAT_ID`)

2. **Bot Settings**:
   Open `config.yaml` to configure the bot's behavior.
   ```yaml
   bot:
     niche: "Artificial Intelligence"
     tone_of_voice: "Expert AI blogger, concise and professional"
     mode: "auto"

   llm:
     base_url: "https://integrate.api.nvidia.com/v1"
     model_name: "deepseek-ai/deepseek-v4-pro"
     # Optional provider-specific kwargs. Safe to delete if using OpenAI or other standards.
     extra_body:
       chat_template_kwargs:
         thinking: False
   ```
   - Set your `niche` and `tone_of_voice`.
   - Set `mode` to `auto` to let the bot find its own sources, or `manual` to strictly use the sources defined in the file.
   - Configure your LLM endpoint in the `llm` section. Change `base_url` and `model_name` as needed (e.g., `https://api.openai.com/v1` and `gpt-4o`).

## Usage

Start the bot by running the main orchestrator:

```bash
python main.py
```

Once running, open your Telegram bot. You can use the following commands:
- `/start` or `/help` - Show the control panel and active settings.
- `/status` - View bot health, pending posts, and the next scheduled run time.
- `/force` - Force an immediate check for new news.

When the bot finds relevant news, it will send a drafted tweet to your Telegram chat. You can click "Approve" to publish it immediately or "Reject" to discard it.

## Architecture Notes

- **Asynchronous Execution**: Network and API calls are wrapped in asynchronous threads to prevent blocking the Telegram interface.
- **Database**: SQLite is configured in Write-Ahead Logging (WAL) mode with connection pooling for safe concurrent access.
- **Media Caching**: Temporary images from news articles are saved in the `images/` directory to survive application restarts, and are automatically cleaned up after you approve or reject a post.

## License

MIT License
