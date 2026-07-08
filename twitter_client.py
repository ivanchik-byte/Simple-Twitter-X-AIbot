import os
import tweepy
import logging
import tempfile

logger = logging.getLogger(__name__)

def post_tweet(text: str, image_bytes: bytes = None) -> bool:
    consumer_key = os.getenv("TWITTER_CONSUMER_KEY")
    consumer_secret = os.getenv("TWITTER_CONSUMER_SECRET")
    access_token = os.getenv("TWITTER_ACCESS_TOKEN")
    access_token_secret = os.getenv("TWITTER_ACCESS_TOKEN_SECRET")
    bearer_token = os.getenv("TWITTER_BEARER_TOKEN")
    
    if not all([consumer_key, consumer_secret, access_token, access_token_secret]):
        logger.warning("Twitter credentials not fully provided. Skipping actual posting.")
        logger.info(f"Would have posted tweet: {text}")
        return False
        
    try:
        auth = tweepy.OAuth1UserHandler(consumer_key, consumer_secret, access_token, access_token_secret)
        api = tweepy.API(auth)
        
        client = tweepy.Client(
            bearer_token=bearer_token,
            consumer_key=consumer_key,
            consumer_secret=consumer_secret,
            access_token=access_token,
            access_token_secret=access_token_secret
        )
        
        media_ids = None
        temp_path = None
        if image_bytes:
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as temp_file:
                temp_file.write(image_bytes)
                temp_path = temp_file.name
                
            try:
                media = api.media_upload(temp_path)
                media_ids = [media.media_id]
            finally:
                if temp_path and os.path.exists(temp_path):
                    os.remove(temp_path)
            
        client.create_tweet(text=text, media_ids=media_ids)
        logger.info("Successfully posted to Twitter.")
        return True
    except Exception as e:
        logger.error(f"Error posting to Twitter: {e}")
        return False
