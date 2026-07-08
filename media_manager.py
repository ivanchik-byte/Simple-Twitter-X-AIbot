import os
import requests
import urllib.parse
from google import genai
import logging
from io import BytesIO
from typing import Optional

logger = logging.getLogger(__name__)

def generate_image_pollinations(prompt: str) -> Optional[bytes]:
    url = f"https://image.pollinations.ai/prompt/{urllib.parse.quote(prompt)}?nologo=true"
    try:
        response = requests.get(url)
        response.raise_for_status()
        return response.content
    except Exception as e:
        logger.error(f"Error generating image with Pollinations: {e}")
        return None

def process_media(post: dict) -> dict:
    """
    Takes a post dict, processes its image or generates a new one.
    Returns the post dict updated with 'chart_description' and 'final_image_bytes'.
    """
    image_url = post.get('image_url')
    final_image_bytes = None
    chart_description = ""
    
    gemini_key = os.getenv("GEMINI_API_KEY")
    
    if image_url:
        try:
            # Download image
            response = requests.get(image_url)
            response.raise_for_status()
            final_image_bytes = response.content
            
            # Send to Gemini
            if gemini_key:
                client = genai.Client(api_key=gemini_key)
                from PIL import Image
                img = Image.open(BytesIO(final_image_bytes))
                
                response = client.models.generate_content(
                    model='gemini-2.5-flash',
                    contents=[
                        "Describe this image. If it is a chart, graph, or data visualization, explain the key data points in detail. If it's just a generic photo, just say 'Generic photo'.",
                        img
                    ]
                )
                desc = response.text
                if "Generic photo" not in desc:
                    chart_description = desc
        except Exception as e:
            logger.error(f"Error processing existing image with Gemini: {e}")
    else:
        # Generate new image prompt using the title
        prompt = f"High quality digital art, expert AI blog style, conceptual illustration of: {post.get('title')}"
        final_image_bytes = generate_image_pollinations(prompt)
        
    post['chart_description'] = chart_description
    post['final_image_bytes'] = final_image_bytes
    return post
