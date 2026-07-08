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
                    "text": entry.summary,
                    "image_url": image_url,
                    "source": source_name
                })
    except Exception as e:
        logger.error(f"Error fetching RSS {url}: {e}")
    return posts

def fetch_subreddit(subreddit: str) -> List[Dict]:
    url = f"https://www.reddit.com/r/{subreddit}/new.json?limit=10"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"}
    posts = []
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        for child in data.get("data", {}).get("children", []):
            post_data = child.get("data", {})
            link = "https://reddit.com" + post_data.get("permalink", "")
            if not is_posted(link):
                image_url = post_data.get("url_overridden_by_dest") if post_data.get("post_hint") == "image" else None
                posts.append({
                    "title": post_data.get("title", ""),
                    "url": link,
                    "text": post_data.get("selftext", ""),
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
        
    for sub in sources.get("subreddits", []):
        new_posts.extend(fetch_subreddit(sub))
        
    return new_posts
