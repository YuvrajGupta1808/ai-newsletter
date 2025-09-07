import requests
import logging
from config import NEWSAPI_KEY
from retry_utils import retry_with_backoff, news_api_circuit_breaker

logger = logging.getLogger(__name__)

@news_api_circuit_breaker
@retry_with_backoff(max_attempts=3, base_delay=1.0, exceptions=(requests.RequestException,))
def fetch_news(topic: str, max_items: int = 3):
    url = "https://newsapi.org/v2/top-headlines"
    params = {"q": topic, "pageSize": max_items, "language": "en", "apiKey": NEWSAPI_KEY}
    try:
        r = requests.get(url, params=params, timeout=30)
        r.raise_for_status()
        articles = r.json().get("articles", [])
        items = []
        for a in articles:
            items.append({
                "title": a.get("title", "No title"),
                "summary": a.get("description", "No summary available."),
                "why_it_matters": f"Shows latest trends in {topic}.",
                "source": (a.get("source") or {}).get("name", ""),
                "url": a.get("url", "#"),
                "published_at": a.get("publishedAt", ""),
            })
        return items
    except Exception as e:
        logger.error(f"NewsAPI failed for {topic}: {e}")
        return []

def build_html(all_news: dict):
    parts = [
        "<html><body style=\"font-family:Arial, sans-serif; background:#f9f9f9; padding:20px;\">",
        "<h1 style=\"color:#333;\">📩 Hello, here are your news highlights</h1>"
    ]
    for topic, stories in all_news.items():
        parts.append(f"<h2 style='color:#4b4bf9;border-bottom:2px solid #eee;padding-bottom:5px;margin-top:20px;'>{topic}</h2>")
        if not stories:
            parts.append(f"<p><i>No news available for {topic} right now.</i></p>")
            continue
        for s in stories:
            title = s.get("title", "No title")
            summary = s.get("summary", "No summary")
            why = s.get("why_it_matters", "N/A")
            url = s.get("url", "#")
            source = s.get("source", "")
            parts.append(
                f"<p><b>{title}</b><br>"
                f"{summary}<br>"
                f"<i>Why it matters:</i> {why}<br>"
                f"<i>Source:</i> {source}<br>"
                f"<a href='{url}' style='color:#4b4bf9;'>Read more</a></p>"
            )
    # Add unsubscribe footer
    parts.append("""
        <div style="margin-top: 40px; padding-top: 20px; border-top: 1px solid #ddd; text-align: center; color: #888; font-size: 12px;">
            <p>You're receiving this because you subscribed to AI Newsletter.</p>
            <p>
                <a href="http://localhost:5000/manage" style="color: #4F46E5;">Manage Preferences</a> | 
                <a href="http://localhost:5000/unsubscribe" style="color: #EF4444;">Unsubscribe</a>
            </p>
            <p>© 2024 AI Newsletter. All rights reserved.</p>
        </div>
    """)
    
    parts.append("</body></html>")
    return "".join(parts)