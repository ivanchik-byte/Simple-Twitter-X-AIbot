import re
from typing import Dict
def generate_tweet_text(post: Dict) -> str:
    tweet = "A new study reveals that despite their sophisticated algorithms, large language models still struggle to accurately simulate human preferences. This means you can't replace UX testing with AI yet! Always rely on real user feedback for critical decisions."
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

print(generate_tweet_text({"url": "https://example.com"}))
