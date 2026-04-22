import os
import requests
from dotenv import load_dotenv

load_dotenv(".env")

NEWS_API_URL = "https://newsapi.org/v2/everything"

def fetch_news(query="geopolitics", page_size=10):
    api_key = os.getenv("NEWS_API_KEY")

    if not api_key:
        return {
            "status": "error",
            "message": "NEWS_API_KEY is missing",
            "articles": []
        }

    try:
        response = requests.get(
            NEWS_API_URL,
            params={
                "q": query,
                "language": "en",
                "pageSize": page_size,
                "sortBy": "publishedAt",
                "apiKey": api_key,
            },
            timeout=30,
        )

        response.raise_for_status()
        data = response.json()

        return data if "articles" in data else {
            "status": "error",
            "message": "Invalid response format",
            "articles": []
        }

    except requests.RequestException as e:
        return {
            "status": "error",
            "message": str(e),
            "articles": []
        }
