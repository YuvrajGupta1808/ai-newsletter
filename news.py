import requests
import logging
import json
from datetime import datetime
from config import PERPLEXITY_API_KEY, NEWSAPI_KEY
from retry_utils import retry_with_backoff

logger = logging.getLogger(__name__)

def sort_news_by_date(news_items):
    """Sort news items by date (newest first)"""
    def get_date_key(item):
        published_at = item.get('published_at', '')
        if not published_at:
            return datetime.min  # Put items without dates at the end
        
        try:
            # Try to parse ISO format
            if 'T' in published_at:
                return datetime.fromisoformat(published_at.replace('Z', '+00:00'))
            # Try other common formats
            elif '-' in published_at:
                return datetime.strptime(published_at, '%Y-%m-%d')
            else:
                return datetime.min
        except:
            return datetime.min
    
    return sorted(news_items, key=get_date_key, reverse=True)

def fetch_news_monthly(topic: str, max_items: int = 10):
    """Fetch news for the past month using News API"""
    if not NEWSAPI_KEY:
        logger.error("NEWSAPI_KEY not configured")
        return []
    
    # Calculate date range (past month)
    from datetime import timedelta
    end_date = datetime.now()
    start_date = end_date - timedelta(days=30)
    
    # Format dates for News API
    from_date = start_date.strftime('%Y-%m-%d')
    to_date = end_date.strftime('%Y-%m-%d')
    
    # Map topics to News API query terms
    topic_mapping = {
        "Technology": "technology OR AI OR artificial intelligence OR software OR tech",
        "Sports": "sports OR football OR basketball OR soccer OR tennis",
        "Politics": "politics OR government OR election OR policy",
        "Finance": "finance OR economy OR business OR stock market OR cryptocurrency"
    }
    
    query = topic_mapping.get(topic, topic)
    
    try:
        url = "https://newsapi.org/v2/everything"
        params = {
            'q': query,
            'from': from_date,
            'to': to_date,
            'sortBy': 'publishedAt',
            'language': 'en',
            'pageSize': max_items * 2,  # Get more to filter and sort
            'apiKey': NEWSAPI_KEY
        }
        
        logger.info(f"Fetching monthly news for {topic} from {from_date} to {to_date}")
        response = requests.get(url, params=params, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        articles = data.get('articles', [])
        
        # Convert to our format
        news_items = []
        for article in articles:
            if article.get('title') and article.get('description'):
                news_item = {
                    'title': article['title'],
                    'summary': article['description'],
                    'url': article.get('url', '#'),
                    'source': article.get('source', {}).get('name', 'Unknown'),
                    'published_at': article.get('publishedAt', ''),
                    'why_it_matters': f"This {topic.lower()} news is significant for staying informed about recent developments and trends in the field."
                }
                news_items.append(news_item)
        
        # Sort by date and limit
        sorted_items = sort_news_by_date(news_items)
        return sorted_items[:max_items]
        
    except requests.exceptions.RequestException as e:
        logger.error(f"News API request failed for {topic}: {e}")
        return []
    except Exception as e:
        logger.error(f"Error processing News API response for {topic}: {e}")
        return []

@retry_with_backoff(max_attempts=3, base_delay=1.0, exceptions=(requests.RequestException,))
def fetch_news_perplexity(topic: str, max_items: int = 2):
    """Fetch news using Perplexity API for more intelligent and comprehensive news"""
    url = "https://api.perplexity.ai/chat/completions"
    
    # Create intelligent prompts for different topics
    topic_prompts = {
        "Technology": f"Find the top {max_items} most important and recent technology news stories from the last 7 days. Include AI, software, hardware, startups, and tech industry developments. For each story, provide: 1) A compelling headline, 2) A detailed summary explaining the significance, 3) Why this matters to tech professionals and enthusiasts, 4) The source/publication, 5) A relevant URL if available, 6) The exact publication date in YYYY-MM-DD format. Format as JSON array with fields: title, summary, why_it_matters, source, url, published_at.",
        
        "Sports": f"Find the top {max_items} most important and recent sports news stories from the last 7 days. Include major leagues (NFL, NBA, MLB, NHL, Premier League, etc.), Olympics, major tournaments, and significant sports developments. For each story, provide: 1) A compelling headline, 2) A detailed summary explaining the significance, 3) Why this matters to sports fans, 4) The source/publication, 5) A relevant URL if available, 6) The exact publication date in YYYY-MM-DD format. Format as JSON array with fields: title, summary, why_it_matters, source, url, published_at.",
        
        "Politics": f"Find the top {max_items} most important and recent political news stories from the last 7 days. Include government policy, elections, international relations, and significant political developments. For each story, provide: 1) A compelling headline, 2) A detailed summary explaining the significance, 3) Why this matters to citizens and policy makers, 4) The source/publication, 5) A relevant URL if available, 6) The exact publication date in YYYY-MM-DD format. Format as JSON array with fields: title, summary, why_it_matters, source, url, published_at.",
        
        "Finance": f"Find the top {max_items} most important and recent financial news stories from the last 7 days. Include market movements, economic policy, corporate earnings, cryptocurrency, and significant financial developments. For each story, provide: 1) A compelling headline, 2) A detailed summary explaining the significance, 3) Why this matters to investors and business professionals, 4) The source/publication, 5) A relevant URL if available, 6) The exact publication date in YYYY-MM-DD format. Format as JSON array with fields: title, summary, why_it_matters, source, url, published_at."
    }
    
    prompt = topic_prompts.get(topic, f"Find the top {max_items} most important and recent news stories about {topic}.")
    
    headers = {
        "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
        "Content-Type": "application/json"
    }
    
    data = {
        "model": "sonar",
        "messages": [
            {
                "role": "system",
                "content": "You are a professional news curator. Provide accurate, well-researched news summaries in JSON format. Always include real, current information with proper sources."
            },
            {
                "role": "user",
                "content": prompt
            }
        ],
        "max_tokens": 2000,
        "temperature": 0.3
    }
    
    try:
        response = requests.post(url, headers=headers, json=data, timeout=60)
        response.raise_for_status()
        
        result = response.json()
        content = result.get("choices", [{}])[0].get("message", {}).get("content", "")
        
        # Try to parse JSON from the response
        try:
            # Extract JSON from the response (it might be wrapped in markdown)
            if "```json" in content:
                json_start = content.find("```json") + 7
                json_end = content.find("```", json_start)
                json_content = content[json_start:json_end].strip()
            elif "```" in content:
                json_start = content.find("```") + 3
                json_end = content.find("```", json_start)
                json_content = content[json_start:json_end].strip()
            else:
                json_content = content.strip()
            
            # Try to parse as JSON array
            news_items = json.loads(json_content)
            if isinstance(news_items, list):
                # Sort by date (newest first) and limit items
                sorted_items = sort_news_by_date(news_items)
                return sorted_items[:max_items]
            elif isinstance(news_items, dict):
                return [news_items]
        except json.JSONDecodeError:
            # If JSON parsing fails, create structured data from text
            logger.warning(f"Failed to parse JSON from Perplexity response for {topic}, creating structured data")
            return create_structured_news_from_text(content, topic, max_items)
        
        return []
        
    except Exception as e:
        logger.error(f"Perplexity API failed for {topic}: {e}")
        # Return empty list if Perplexity fails
        return []

def create_structured_news_from_text(content: str, topic: str, max_items: int):
    """Create structured news data from Perplexity text response when JSON parsing fails"""
    items = []
    lines = content.split('\n')
    current_item = {}
    
    for line in lines:
        line = line.strip()
        if not line:
            if current_item:
                items.append(current_item)
                current_item = {}
            continue
            
        if line.lower().startswith('title:') or line.lower().startswith('headline:'):
            current_item['title'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('summary:'):
            current_item['summary'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('why it matters:') or line.lower().startswith('significance:'):
            current_item['why_it_matters'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('source:'):
            current_item['source'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('url:'):
            current_item['url'] = line.split(':', 1)[1].strip()
        elif line.lower().startswith('published:'):
            current_item['published_at'] = line.split(':', 1)[1].strip()
    
    # Add the last item if exists
    if current_item:
        items.append(current_item)
    
    # Ensure all items have required fields
    for item in items:
        item.setdefault('title', f'Latest {topic} News')
        item.setdefault('summary', f'Important development in {topic}')
        item.setdefault('why_it_matters', f'This story is significant for {topic} enthusiasts and professionals')
        item.setdefault('source', 'Perplexity AI')
        item.setdefault('url', '#')
        item.setdefault('published_at', datetime.now().strftime('%Y-%m-%dT%H:%M:%SZ'))
    
    # Sort by date and limit items
    sorted_items = sort_news_by_date(items)
    return sorted_items[:max_items]

def build_html(all_news: dict, base_url: str = "http://localhost:5000"):
    """Build a professional, modern email template for news"""
    current_date = datetime.now().strftime("%B %d, %Y")
    current_time = datetime.now().strftime("%I:%M %p")
    
    parts = [
        f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>AI Newsletter - Daily Digest</title>
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
        
        .email-container {{
            max-width: 800px;
            margin: 0 auto;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
        }}
        
        .header {{
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            padding: 60px 50px;
            text-align: center;
            position: relative;
            overflow: hidden;
        }}
        
        .header::before {{
            content: '';
            position: absolute;
            top: -50%;
            left: -50%;
            width: 200%;
            height: 200%;
            background: radial-gradient(circle, rgba(255,255,255,0.1) 0%, transparent 70%);
            animation: float 6s ease-in-out infinite;
        }}
        
        @keyframes float {{
            0%, 100% {{ transform: translateY(0px) rotate(0deg); }}
            50% {{ transform: translateY(-20px) rotate(180deg); }}
        }}
        
        .header-content {{
            position: relative;
            z-index: 2;
        }}
        
        .logo {{
            font-family: 'Inter', sans-serif;
            font-size: 48px;
            font-weight: 800;
            color: #ffffff;
            margin: 0 0 16px 0;
            letter-spacing: -1px;
            text-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        
        .tagline {{
            font-family: 'Inter', sans-serif;
            font-size: 20px;
            font-weight: 500;
            color: #e2e8f0;
            margin: 0 0 12px 0;
            letter-spacing: 0.5px;
        }}
        
        .date-time {{
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            color: #cbd5e1;
            margin: 0;
            font-weight: 400;
        }}
        
        .content {{
            background: #ffffff;
            padding: 60px 50px;
        }}
        
        .intro {{
            text-align: center;
            margin-bottom: 60px;
        }}
        
        .intro h2 {{
            font-family: 'Inter', sans-serif;
            font-size: 32px;
            font-weight: 700;
            color: #1e293b;
            margin: 0 0 20px 0;
            letter-spacing: -0.5px;
        }}
        
        .intro p {{
            font-family: 'Inter', sans-serif;
            font-size: 18px;
            color: #64748b;
            margin: 0;
            line-height: 1.6;
            max-width: 600px;
            margin: 0 auto;
        }}
        
        .topic-section {{
            margin-bottom: 60px;
        }}
        
        .topic-header {{
            display: flex;
            align-items: center;
            margin-bottom: 40px;
            padding-bottom: 20px;
            border-bottom: 3px solid #f1f5f9;
        }}
        
        .topic-icon {{
            font-size: 32px;
            margin-right: 20px;
            filter: drop-shadow(0 2px 4px rgba(0,0,0,0.1));
        }}
        
        .topic-title {{
            font-family: 'Inter', sans-serif;
            font-size: 26px;
            font-weight: 700;
            color: #1e293b;
            margin: 0;
            letter-spacing: -0.3px;
        }}
        
        .news-card {{
            background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
            border-radius: 20px;
            padding: 40px;
            margin-bottom: 35px;
            border: 1px solid #e2e8f0;
            box-shadow: 0 6px 20px rgba(0, 0, 0, 0.08);
            transition: all 0.3s ease;
            position: relative;
            overflow: hidden;
        }}
        
        .news-card::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            width: 4px;
            height: 100%;
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
        }}
        
        .news-card:hover {{
            transform: translateY(-2px);
            box-shadow: 0 8px 25px rgba(0, 0, 0, 0.1);
        }}
        
        .news-header {{
            display: flex;
            justify-content: space-between;
            align-items: flex-start;
            margin-bottom: 25px;
        }}
        
        .news-title {{
            font-family: 'Inter', sans-serif;
            font-size: 22px;
            font-weight: 700;
            color: #1e293b;
            margin: 0;
            line-height: 1.4;
            flex: 1;
            margin-right: 20px;
        }}
        
        .news-badge {{
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
            color: #ffffff;
            font-family: 'Inter', sans-serif;
            font-size: 12px;
            font-weight: 600;
            padding: 6px 12px;
            border-radius: 20px;
            white-space: nowrap;
            box-shadow: 0 2px 4px rgba(59, 130, 246, 0.3);
        }}
        
        .news-summary {{
            font-family: 'Inter', sans-serif;
            font-size: 17px;
            color: #475569;
            line-height: 1.7;
            margin: 0 0 25px 0;
        }}
        
        .why-matters {{
            background: linear-gradient(135deg, #fef3c7 0%, #fde68a 100%);
            border: 1px solid #f59e0b;
            border-radius: 16px;
            padding: 25px;
            margin: 25px 0;
            position: relative;
        }}
        
        .why-matters::before {{
            content: '💡';
            position: absolute;
            top: -8px;
            left: 20px;
            background: #ffffff;
            padding: 0 8px;
            font-size: 16px;
        }}
        
        .why-matters-title {{
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            font-weight: 700;
            color: #92400e;
            margin: 0 0 8px 0;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}
        
        .why-matters-text {{
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            color: #92400e;
            margin: 0;
            line-height: 1.5;
        }}
        
        .news-footer {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-top: 25px;
            padding-top: 25px;
            border-top: 1px solid #e2e8f0;
        }}
        
        .news-meta {{
            display: flex;
            align-items: center;
            gap: 25px;
        }}
        
        .meta-item {{
            font-family: 'Inter', sans-serif;
            font-size: 13px;
            color: #64748b;
            font-weight: 500;
            display: flex;
            align-items: center;
            gap: 6px;
        }}
        
        .read-more-btn {{
            background: linear-gradient(135deg, #3b82f6 0%, #8b5cf6 100%);
            color: #ffffff;
            text-decoration: none;
            font-family: 'Inter', sans-serif;
            font-size: 14px;
            font-weight: 600;
            padding: 12px 24px;
            border-radius: 25px;
            box-shadow: 0 4px 12px rgba(59, 130, 246, 0.3);
            transition: all 0.3s ease;
        }}
        
        .read-more-btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 6px 20px rgba(59, 130, 246, 0.4);
        }}
        
        .footer {{
            background: linear-gradient(135deg, #f8fafc 0%, #e2e8f0 100%);
            padding: 50px;
            text-align: center;
            border-top: 1px solid #e2e8f0;
        }}
        
        .footer-content {{
            margin-bottom: 40px;
        }}
        
        .footer h4 {{
            font-family: 'Inter', sans-serif;
            font-size: 20px;
            font-weight: 700;
            color: #1e293b;
            margin: 0 0 16px 0;
        }}
        
        .footer p {{
            font-family: 'Inter', sans-serif;
            font-size: 16px;
            color: #64748b;
            margin: 0;
            line-height: 1.6;
            max-width: 500px;
            margin: 0 auto;
        }}
        
        .footer-actions {{
            display: flex;
            justify-content: center;
            gap: 25px;
            margin: 40px 0;
        }}
        
        .footer-btn {{
            font-family: 'Inter', sans-serif;
            font-size: 15px;
            font-weight: 600;
            padding: 14px 28px;
            border-radius: 25px;
            text-decoration: none;
            transition: all 0.3s ease;
        }}
        
        .footer-btn.manage {{
            background: #3b82f6;
            color: #ffffff;
            border: 1px solid #3b82f6;
        }}
        
        .footer-btn.unsubscribe {{
            background: #ffffff;
            color: #ef4444;
            border: 1px solid #ef4444;
        }}
        
        .footer-btn:hover {{
            transform: translateY(-1px);
            box-shadow: 0 4px 12px rgba(0, 0, 0, 0.1);
        }}
        
        .footer-bottom {{
            border-top: 1px solid #e2e8f0;
            padding-top: 20px;
            margin-top: 20px;
        }}
        
        .footer-bottom p {{
            font-family: 'Inter', sans-serif;
            font-size: 12px;
            color: #94a3b8;
            margin: 0 0 8px 0;
        }}
        
        .powered-by {{
            font-family: 'Inter', sans-serif;
            font-size: 12px;
            color: #94a3b8;
            margin: 0;
            font-weight: 500;
        }}
        
        @media (max-width: 600px) {{
            .email-container {{
                margin: 0;
                border-radius: 0;
            }}
            
            .header, .content, .footer {{
                padding: 40px 25px;
            }}
            
            .logo {{
                font-size: 36px;
            }}
            
            .tagline {{
                font-size: 18px;
            }}
            
            .intro h2 {{
                font-size: 28px;
            }}
            
            .intro p {{
                font-size: 16px;
            }}
            
            .topic-title {{
                font-size: 22px;
            }}
            
            .news-card {{
                padding: 30px;
                margin-bottom: 30px;
            }}
            
            .news-title {{
                font-size: 20px;
            }}
            
            .news-summary {{
                font-size: 16px;
            }}
            
            .news-header {{
                flex-direction: column;
                align-items: flex-start;
            }}
            
            .news-badge {{
                margin-top: 12px;
            }}
            
            .news-footer {{
                flex-direction: column;
                align-items: flex-start;
                gap: 20px;
            }}
            
            .footer-actions {{
                flex-direction: column;
                align-items: center;
                gap: 15px;
            }}
        }}
    </style>
</head>
<body style="margin: 0; padding: 30px; background-color: #f1f5f9; font-family: 'Inter', sans-serif;">
    <div class="email-container">
        
        <!-- Header -->
        <div class="header">
            <div class="header-content">
                <h1 class="logo">AI Newsletter</h1>
                <p class="tagline">Your Daily Intelligence Digest</p>
                <p class="date-time">{current_date} • {current_time}</p>
            </div>
        </div>
        
        <!-- Main Content -->
        <div class="content">
            <div class="intro">
                <h2>Today's Top Stories</h2>
                <p>Curated insights powered by AI to keep you informed and ahead of the curve</p>
            </div>
        """
    ]
    
    # Add news sections
    for topic, stories in all_news.items():
        if not stories:
            continue
            
        # Topic header with icon
        topic_icons = {
            "Technology": "💻",
            "Sports": "⚽",
            "Politics": "🏛️",
            "Finance": "💰"
        }
        icon = topic_icons.get(topic, "📰")
        
        parts.append(f"""
            <div class="topic-section">
                <div class="topic-header">
                    <span class="topic-icon">{icon}</span>
                    <h3 class="topic-title">{topic}</h3>
                </div>
        """)
        
        # Add stories
        for i, story in enumerate(stories, 1):
            title = story.get("title", "No title")
            summary = story.get("summary", "No summary available")
            why_matters = story.get("why_it_matters", "")
            url = story.get("url", "#")
            source = story.get("source", "Various Sources")
            published_at = story.get("published_at", "")
            
            # Format published date
            try:
                if published_at:
                    pub_date = datetime.fromisoformat(published_at.replace('Z', '+00:00'))
                    formatted_date = pub_date.strftime("%b %d, %Y")
                else:
                    formatted_date = "Recent"
            except:
                formatted_date = "Recent"
            
            parts.append(f"""
                <div class="news-card">
                    <div class="news-header">
                        <h4 class="news-title">{title}</h4>
                        <span class="news-badge">#{i}</span>
                    </div>
                    
                    <p class="news-summary">{summary}</p>
                    
                    {f'<div class="why-matters"><div class="why-matters-title">Why This Matters</div><div class="why-matters-text">{why_matters}</div></div>' if why_matters else ''}
                    
                    <div class="news-footer">
                        <div class="news-meta">
                            <div class="meta-item">📅 {formatted_date}</div>
                            <div class="meta-item">📰 {source}</div>
                        </div>
                        {f'<a href="{url}" class="read-more-btn">Read More →</a>' if url != '#' else ''}
                    </div>
                </div>
            """)
        
        parts.append("</div>")
    
    # Add footer
    parts.append(f"""
        </div>
        
        <!-- Footer -->
        <div class="footer">
            <div class="footer-content">
                <h4>Stay Connected</h4>
                <p>Thank you for being part of our community. We're committed to delivering the most relevant and insightful news to keep you ahead of the curve.</p>
            </div>
            
            <div class="footer-actions">
                <a href="{base_url}/manage" class="footer-btn manage">Manage Preferences</a>
                <a href="{base_url}/unsubscribe" class="footer-btn unsubscribe">Unsubscribe</a>
            </div>
            
            <div class="footer-bottom">
            <p>You're receiving this because you subscribed to AI Newsletter.</p>
                <p class="powered-by">© 2025 AI Newsletter. All rights reserved. | Powered by Perplexity AI</p>
            </div>
        </div>
    </div>
</body>
</html>
    """)
    
    return "".join(parts)