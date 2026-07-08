import sqlite3
import feedparser
import requests
import logging
from typing import List, Dict, Optional
from researcher import discover_sources
from config import load_config

logger = logging.getLogger(__name__)
DB_PATH = "posted_urls.db"

_conn: Optional[sqlite3.Connection] = None

def get_conn() -> sqlite3.Connection:
    global _conn
    if _conn is None:
        _conn = sqlite3.connect(DB_PATH, check_same_thread=False)
        _conn.execute("PRAGMA journal_mode=WAL")
        _conn.execute(
            "CREATE TABLE IF NOT EXISTS posts (url TEXT PRIMARY KEY, source TEXT)"
        )
    return _conn

def is_posted(url: str) -> bool:
    cur = get_conn().execute("SELECT 1 FROM posts WHERE url = ?", (url,))
    return cur.fetchone() is not None

def mark_posted(url: str, source: str):
    try:
        get_conn().execute(
            "INSERT OR IGNORE INTO posts (url, source) VALUES (?, ?)",
            (url, source)
        )
        get_conn().commit()
    except Exception as e:
        logger.error(f"Error marking post: {e}")
        get_conn().rollback()

def fetch_rss(url: str, source_name: str) -> List[Dict]:
    posts = []
    try:
        feed = feedparser.parse(url)
        for entry in feed.entries[:10]:
            link = entry.link
            if not is_posted(link):
                image_url = None
                if 'media_content' in entry and len(entry.media_content) > 0:
                    image_url = entry.media_content[0].get('url')
                elif 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
                    image_url = entry.media_thumbnail[0].get('url')
                
                posts.append({
                    "title": entry.title,
                    "url": link,
                    "text": getattr(entry, 'summary', getattr(entry, 'description', '')),
                    "image_url": image_url,
                    "source": source_name
                })
    except Exception as e:
        logger.error(f"Error fetching RSS {url}: {e}")
    return posts

def fetch_subreddit(subreddit: str) -> List[Dict]:
    url = f"https://www.reddit.com/r/{subreddit}/.rss?limit=10"
    posts = []
    user_agents = [
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
        "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2.1 Safari/605.1.15",
        "Mozilla/5.0 (X11; Linux x86_64; rv:121.0) Gecko/20100101 Firefox/121.0"
    ]
    import random
    import time
    headers = {"User-Agent": random.choice(user_agents)}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        if response.status_code == 429:
            logger.warning(f"Reddit 429 Rate Limit for {subreddit}. Sleeping 3s...")
            time.sleep(3)
            response = requests.get(url, headers=headers, timeout=10)
            
        response.raise_for_status()
        
        feed = feedparser.parse(response.content)
        for entry in feed.entries[:10]:
            link = entry.link
            if not is_posted(link):
                image_url = None
                if 'media_thumbnail' in entry and len(entry.media_thumbnail) > 0:
                    image_url = entry.media_thumbnail[0].get('url')
                elif 'media_content' in entry and len(entry.media_content) > 0:
                    image_url = entry.media_content[0].get('url')
                
                posts.append({
                    "title": entry.title,
                    "url": link,
                    "text": getattr(entry, 'summary', getattr(entry, 'description', '')),
                    "image_url": image_url,
                    "source": f"reddit_{subreddit}"
                })
    except Exception as e:
        logger.error(f"Error fetching Reddit {subreddit}: {e}")
    return posts

def get_new_posts() -> List[Dict]:
    get_conn() # Ensure DB init
    config = load_config()
    
    bot_config = config.get("bot", {})
    mode = bot_config.get("mode", "manual")
    niche = bot_config.get("niche", "Artificial Intelligence")
    
    sources = {"rss": [], "subreddits": []}
    
    if mode == "auto":
        sources = discover_sources(niche)
    else:
        sources = config.get("sources", {})
        if not sources:
            sources = {"rss": [], "subreddits": []}
            
    new_posts = []
    
    for rss_url in sources.get("rss", []):
        new_posts.extend(fetch_rss(rss_url, "rss"))
        
    import time
    for sub in sources.get("subreddits", []):
        new_posts.extend(fetch_subreddit(sub))
        time.sleep(1.5) # Sleep between subreddits to avoid 429
        
    if not new_posts:
        logger.warning("No posts found from sources (possibly blocked or bad feeds). Using fallbacks...")
        fallbacks = [
            "https://cointelegraph.com/rss/tag/artificial-intelligence",
            "https://www.artificialintelligence-news.com/feed/",
            "https://dev.to/feed/tag/ai"
        ]
        for url in fallbacks:
            new_posts.extend(fetch_rss(url, "fallback_rss"))
            
    return new_posts
