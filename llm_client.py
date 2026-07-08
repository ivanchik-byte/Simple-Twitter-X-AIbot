import os
import json
from openai import OpenAI
import logging
import re
from typing import List, Dict, Optional
from config import load_config

logger = logging.getLogger(__name__)

def select_best_post(posts: List[Dict]) -> Optional[Dict]:
    if not posts: return None
    if len(posts) == 1: return posts[0]
    
    config = load_config()
    llm_config = config.get("llm", {})
    base_url = llm_config.get("base_url", "https://integrate.api.nvidia.com/v1")
    model_name = llm_config.get("model_name", "deepseek-ai/deepseek-v4-pro")
    llm_key = os.getenv("LLM_API_KEY")
    
    if not llm_key or llm_key == "your_llm_api_key_here":
        return posts[0]
        
    client = OpenAI(base_url=base_url, api_key=llm_key)
    bot_config = config.get("bot", {})
    niche = bot_config.get("niche", "Artificial Intelligence")
    
    posts_text = ""
    for idx, p in enumerate(posts):
        title = p.get('title', '').replace('\n', ' ')
        summary = p.get('text', '').replace('\n', ' ')[:300]
        posts_text += f"ID: {idx}\nTitle: {title}\nSummary: {summary}\n\n"
        
    prompt = (
        f"You are an expert content curator for a highly engaging Twitter account in the niche of '{niche}'.\n"
        "Here are several news items I have fetched:\n\n"
        f"{posts_text}\n"
        "Your task is to select the SINGLE MOST interesting, viral, and engaging news item that people would desperately want to read.\n\n"
        "CRITICAL FILTERING RULES:\n"
        "You MUST absolutely IGNORE and DISCARD any posts that look like:\n"
        "- Advertisements or sponsored posts\n"
        "- Affiliate marketing or referral links\n"
        "- 'How I made $X' stories or course selling\n"
        "- Self-promotion or spam\n\n"
        "Return ONLY a valid JSON object with a single key 'best_id' whose value is the integer ID of the chosen post. Do not include any other text."
    )
    
    try:
        completion_kwargs = {
            "model": model_name,
            "messages": [{"role":"user","content": prompt}],
            "temperature": 0.2,
            "max_tokens": 50,
            "stream": False
        }
        if "extra_body" in llm_config:
            completion_kwargs["extra_body"] = llm_config["extra_body"]
            
        completion = client.chat.completions.create(**completion_kwargs)
        result_text = completion.choices[0].message.content.strip()
        
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if json_match:
            data = json.loads(json_match.group(0))
            best_id = int(data.get("best_id", 0))
            if 0 <= best_id < len(posts):
                return posts[best_id]
    except Exception as e:
        logger.error(f"Error selecting best post: {e}")
        
    return posts[0]

def generate_tweet_text(post: dict, rewrite: bool = False) -> str:
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
        
    custom_prompt = bot_config.get("prompt", "")
    
    base_instructions = f"""You are an elite Twitter (X) ghostwriter and social media strategist operating in the '{niche}' niche.
Your goal is to write a highly engaging, viral, and concise post based on the provided news content.
Tone of Voice: {tone}

CRITICAL RULES:
1. LENGTH LIMIT: The tweet text MUST be around 200-240 characters. DO NOT leave hanging sentences or end with '...'. Finish your thought naturally!
2. FORMATTING: Use X-style formatting. Keep paragraphs to 1-2 short sentences. Use line breaks for readability. Do not output a single wall of text.
3. HOOK: Start with a powerful, scroll-stopping hook. Do not use cliché openings like "Breaking News:", "Did you know?", or "In a shocking turn of events".
4. EMOJIS: Use a maximum of 1 or 2 relevant emojis. Do not overdo it.
5. NO HASHTAGS & NO LINKS: Do not use hashtags. Do NOT include any URLs or links in your text (they will be added automatically later).
6. OUTPUT: ONLY output the final tweet text. No introductory phrases, no quotation marks around the tweet, no meta-commentary.
"""
    
    if os.path.exists("post_history.json"):
        try:
            with open("post_history.json", 'r') as f:
                history = json.load(f)
                if history:
                    recent = "\n".join([f"- {h['text']}" for h in history[:5]])
                    base_instructions += f"\nCRITICAL: DO NOT REPEAT THESE RECENT TOPICS OR PHRASES:\n{recent}\n"
        except Exception:
            pass
    
    if custom_prompt:
        base_instructions += f"\nADDITIONAL CUSTOM INSTRUCTIONS:\n{custom_prompt}\n"
        
    if rewrite:
        base_instructions += "\nCRITICAL: You are REWRITING a previously generated tweet because the user rejected it. You MUST use a completely different hook, a different structure, and ensure it is extremely catchy and viral. Do not repeat the same text.\n"
        
    prompt = f"{base_instructions}\nNews Content:\n{content}"
    
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
        tweet = tweet.replace('<br>', '\n').replace('<br/>', '\n')
        
        # Enforce strict text length before adding URL (max 250 to allow space for link)
        if len(tweet) > 250:
            match = re.search(r'(?s:.*)[.!?]', tweet[:250])
            if match:
                tweet = match.group(0)
            else:
                tweet = tweet[:247] + "..."
                
        # Append Source URL if available
        url = post.get('url')
        if url:
            tweet = f"{tweet}\n\n{url}"
            
        return tweet
    except Exception as e:
        logger.error(f"Error generating tweet with DeepSeek: {e}")
        return f"{title} #{niche.replace(' ', '')}"
