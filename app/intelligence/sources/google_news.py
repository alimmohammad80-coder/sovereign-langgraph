import requests
import xml.etree.ElementTree as ET
from urllib.parse import quote_plus
from typing import List, Dict, Any


def fetch_google_news(query: str, limit: int = 10) -> List[Dict[str, Any]]:
    encoded_query = quote_plus(query)
    url = f"https://news.google.com/rss/search?q={encoded_query}&hl=en-US&gl=US&ceid=US:en"

    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        items = []

        for item in root.findall(".//item")[:limit]:
            title = item.findtext("title") or "Untitled"
            link = item.findtext("link")
            published = item.findtext("pubDate")
            source_node = item.find("source")
            source = source_node.text if source_node is not None else "Google News RSS"

            items.append({
                "title": title,
                "summary": title,
                "source": source,
                "url": link,
                "published_at": published,
                "domain": "live_news"
            })

        return items

    except Exception as e:
        return [{
            "title": "Google News fetch failed",
            "summary": str(e),
            "source": "Google News RSS",
            "url": None,
            "domain": "system_error"
        }]
