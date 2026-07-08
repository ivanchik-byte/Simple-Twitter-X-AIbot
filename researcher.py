import os
import json
import logging
import re
from ddgs import DDGS
from openai import OpenAI
from config import load_config

logger = logging.getLogger(__name__)
CACHE_FILE = "auto_sources.json"

def perform_search(query: str) -> str:
    logger.info(f"Searching DuckDuckGo for: {query}")
    try:
        ddgs = DDGS()
        results = list(ddgs.text(query, max_results=10))
        text = "\n".join([f"{r.get('title', '')} - {r.get('href', '')} - {r.get('body', '')}" for r in results])
        return text
    except Exception as e:
        logger.error(f"DuckDuckGo search error: {e}")
        return ""

def discover_sources(niche: str) -> dict:
    if os.path.exists(CACHE_FILE):
        logger.info("Loading cached sources from auto_sources.json")
        try:
            with open(CACHE_FILE, 'r') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {CACHE_FILE}: {e}")

    logger.info(f"Discovering new sources for niche: {niche}")
    
    search_text_rss = perform_search(f"best RSS feeds for {niche} news")
    search_text_reddit = perform_search(f"best reddit subreddits for {niche}")
    
    config = load_config()
    llm_config = config.get("llm", {})
    base_url = llm_config.get("base_url", "https://integrate.api.nvidia.com/v1")
    model_name = llm_config.get("model_name", "deepseek-ai/deepseek-v4-pro")

    llm_key = os.getenv("LLM_API_KEY")
    if not llm_key or llm_key == "your_llm_api_key_here":
        logger.error("Valid LLM_API_KEY required for auto-research.")
        return {"rss": [], "subreddits": []}
        
    client = OpenAI(
        base_url=base_url,
        api_key=llm_key
    )
    
    prompt = (
        f"You are an AI assistant. I searched the web for RSS feeds and subreddits about '{niche}'.\n"
        "Here are the search results for RSS:\n"
        f"{search_text_rss}\n\n"
        "Here are the search results for Subreddits:\n"
        f"{search_text_reddit}\n\n"
        "Extract the top 5 most relevant and reliable RSS feed URLs and the top 5 Subreddit names (just the name, no 'r/').\n"
        "IMPORTANT: For RSS, ensure the URLs are direct links to raw XML feeds (e.g., ending in .xml, /feed, or /rss), NOT links to HTML articles *about* RSS feeds. If you can't find raw XML feed URLs in the text, guess standard feed endpoints for major sites mentioned (like appending /feed/ to their domain).\n"
        "Return ONLY a valid JSON object with keys 'rss' and 'subreddits' containing lists of strings."
    )
    
    try:
        completion_kwargs = {
            "model": model_name,
            "messages": [{"role":"user","content": prompt}],
            "temperature": 0.2,
            "top_p": 0.95,
            "max_tokens": 500,
            "stream": False
        }
        if "extra_body" in llm_config:
            completion_kwargs["extra_body"] = llm_config["extra_body"]
            
        completion = client.chat.completions.create(**completion_kwargs)
        result_text = completion.choices[0].message.content.strip()
        
        json_match = re.search(r'\{.*\}', result_text, re.DOTALL)
        if not json_match:
            raise ValueError("No JSON object found in response.")
            
        sources = json.loads(json_match.group(0))
        
        if not isinstance(sources, dict):
            raise ValueError("Parsed JSON is not a dictionary.")
            
        valid_sources = {
            "rss": [str(url) for url in sources.get("rss", []) if isinstance(url, str)],
            "subreddits": [str(sub) for sub in sources.get("subreddits", []) if isinstance(sub, str)]
        }
        
        with open(CACHE_FILE, 'w') as f:
            json.dump(valid_sources, f, indent=4)
            
        logger.info(f"Discovered sources: {valid_sources}")
        return valid_sources
        
    except Exception as e:
        logger.error(f"Error extracting sources with DeepSeek: {e}")
        return {"rss": [], "subreddits": []}
