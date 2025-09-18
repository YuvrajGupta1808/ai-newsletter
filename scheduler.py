"""
Newsletter Scheduler - Sends daily newsletters at 8 AM
"""
import schedule
import time
import threading
from datetime import datetime
import logging
from sheets import get_all_verified_subscribers
from news import fetch_news_perplexity, build_html
from mailer import send_email
from config import TOPICS, BASE_URL

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def send_daily_newsletters():
    """
    Send daily newsletters to all verified subscribers
    """
    try:
        logger.info("🕗 Starting daily newsletter sending...")
        
        # Get all verified subscribers
        subscribers = get_all_verified_subscribers()
        
        if not subscribers:
            logger.info("📭 No verified subscribers found")
            return
        
        logger.info(f"📧 Found {len(subscribers)} verified subscribers")
        
        sent_count = 0
        failed_count = 0
        
        for subscriber in subscribers:
            try:
                email = subscriber.get('Email', '').strip()
                if not email:
                    continue
                
                # Get subscriber's preferences
                selected_topics = []
                for topic in TOPICS:
                    if str(subscriber.get(topic, '')).upper() == 'TRUE':
                        selected_topics.append(topic)
                
                if not selected_topics:
                    logger.warning(f"⚠️ No topics selected for {email}")
                    continue
                
                # Get max items preference
                max_items = int(subscriber.get('Max_items', '3') or 3)
                
                # Fetch news for selected topics using Perplexity
                all_news = {}
                for topic in selected_topics:
                    try:
                        news = fetch_news_perplexity(topic, max_items)
                        if news:
                            all_news[topic] = news
                    except Exception as e:
                        logger.error(f"❌ Failed to fetch news for {topic}: {e}")
                        continue
                
                if not all_news:
                    logger.warning(f"⚠️ No news available for {email}")
                    continue
                
                # Build HTML newsletter
                html_content = build_html(all_news, BASE_URL)
                
                # Send email
                subject = f"Your Daily Digest - {', '.join(selected_topics)}"
                success = send_email(email, subject, html_content)
                
                if success:
                    sent_count += 1
                    logger.info(f"✅ Newsletter sent to {email}")
                else:
                    failed_count += 1
                    logger.error(f"❌ Failed to send newsletter to {email}")
                
                # Small delay to avoid overwhelming email servers
                time.sleep(1)
                
            except Exception as e:
                failed_count += 1
                logger.error(f"❌ Error processing subscriber {email}: {e}")
                continue
        
        logger.info(f"📊 Newsletter sending complete: {sent_count} sent, {failed_count} failed")
        
    except Exception as e:
        logger.error(f"❌ Critical error in daily newsletter sending: {e}")

def start_scheduler():
    """
    Start the newsletter scheduler in a background thread
    """
    try:
        # Schedule daily newsletter at 8:00 AM
        schedule.every().day.at("08:00").do(send_daily_newsletters)
        
        logger.info("⏰ Newsletter scheduler started - Daily newsletters at 8:00 AM")
        
        # Run scheduler in background
        def run_scheduler():
            while True:
                schedule.run_pending()
                time.sleep(60)  # Check every minute
        
        scheduler_thread = threading.Thread(target=run_scheduler, daemon=True)
        scheduler_thread.start()
        
        logger.info("🚀 Background scheduler thread started")
        
    except Exception as e:
        logger.error(f"❌ Failed to start scheduler: {e}")

def send_test_newsletter():
    """
    Send a test newsletter to verify the system works
    """
    try:
        logger.info("🧪 Sending test newsletter...")
        send_daily_newsletters()
        logger.info("✅ Test newsletter completed")
    except Exception as e:
        logger.error(f"❌ Test newsletter failed: {e}")

if __name__ == "__main__":
    # For testing - send newsletter immediately
    send_test_newsletter()
