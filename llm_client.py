import os
from openai import OpenAI
import logging
import re
from config import load_config

logger = logging.getLogger(__name__)

def generate_tweet_text(post: dict) -> str:
    config = load_config()
    llm_config = config.get("llm", {})
    base_url = llm_config.get("base_url", "https://integrate.api.nvidia.com/v1")
    model_name = llm_config.get("model_name", "deepseek-ai/deepseek-v4-pro")

    llm_key = os.getenv("LLM_API_KEY")
    if not llm_key or llm_key == "your_llm_api_key_here":
        logger.error("No valid LLM_API_KEY found.")
        return "New update! #News"
        
    client = OpenAI(
        base_url=base_url,
        api_key=llm_key
    )
    
    bot_config = config.get("bot", {})
    niche = bot_config.get("niche", "Artificial Intelligence")
    tone = bot_config.get("tone_of_voice", "Expert blogger")
    
    title = post.get('title', '')
    text = post.get('text', '')
    chart_desc = post.get('chart_description', '')
    
    content = f"Title: {title}\nSummary: {text}\n"
    if chart_desc:
        content += f"Chart/Image Details: {chart_desc}\n"
        
    prompt = (
        f"You are a {tone} on Twitter, focused on the niche of '{niche}'.\n"
        "Write a short, engaging tweet about the provided news. "
        "Rules:\n"
        "1. MUST be under 280 characters.\n"
        "2. MUST be plain text ONLY. DO NOT use markdown, asterisks, bold, or italics.\n"
        "3. Include 1-2 relevant hashtags.\n"
        "4. You can use emojis.\n"
        "5. Keep it professional yet engaging.\n"
        f"News Content:\n{content}"
    )
    
    try:
        completion_kwargs = {
            "model": model_name,
            "messages": [{"role":"user","content": prompt}],
            "temperature": 0.7,
            "top_p": 0.95,
            "max_tokens": 150,
            "stream": False
        }
        if "extra_body" in llm_config:
            completion_kwargs["extra_body"] = llm_config["extra_body"]
            
        completion = client.chat.completions.create(**completion_kwargs)
        tweet = completion.choices[0].message.content.strip()
        
        # Safely remove markdown syntax without stripping all natural asterisks
        tweet = re.sub(r'\*\*(.*?)\*\*', r'\1', tweet)
        tweet = re.sub(r'\*(.*?)\*', r'\1', tweet)
        tweet = re.sub(r'\_(.*?)\_', r'\1', tweet)
        
        if len(tweet) > 280:
            tweet = tweet[:277] + "..."
        return tweet
    except Exception as e:
        logger.error(f"Error generating tweet with DeepSeek: {e}")
        return f"{title} #{niche.replace(' ', '')}"
