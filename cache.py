"""
Simple caching system for news data
Falls back to in-memory cache if Redis is not available
"""
import json
import time
import logging
from typing import Optional, Any

logger = logging.getLogger(__name__)

class SimpleCache:
    """Simple in-memory cache with TTL support"""
    
    def __init__(self):
        self._cache = {}
        self._timestamps = {}
    
    def get(self, key: str) -> Optional[Any]:
        """Get item from cache if not expired"""
        if key not in self._cache:
            return None
            
        # Check if expired
        if key in self._timestamps:
            if time.time() > self._timestamps[key]:
                self.delete(key)
                return None
        
        return self._cache[key]
    
    def set(self, key: str, value: Any, ttl_seconds: int = 300):
        """Set item in cache with TTL"""
        self._cache[key] = value
        self._timestamps[key] = time.time() + ttl_seconds
    
    def delete(self, key: str):
        """Delete item from cache"""
        self._cache.pop(key, None)
        self._timestamps.pop(key, None)
    
    def clear(self):
        """Clear entire cache"""
        self._cache.clear()
        self._timestamps.clear()

# Try to use Redis, fall back to in-memory
try:
    import redis
    
    class RedisCache:
        """Redis-based cache"""
        
        def __init__(self, host='localhost', port=6379, db=0):
            try:
                self.redis_client = redis.Redis(host=host, port=port, db=db, decode_responses=True)
                # Test connection
                self.redis_client.ping()
                logger.info("Connected to Redis for caching")
            except Exception as e:
                logger.warning(f"Could not connect to Redis: {e}. Falling back to in-memory cache.")
                self.redis_client = None
        
        def get(self, key: str) -> Optional[Any]:
            if not self.redis_client:
                return None
            try:
                data = self.redis_client.get(key)
                if data:
                    return json.loads(data)
                return None
            except Exception as e:
                logger.error(f"Redis get error: {e}")
                return None
        
        def set(self, key: str, value: Any, ttl_seconds: int = 300):
            if not self.redis_client:
                return
            try:
                self.redis_client.setex(key, ttl_seconds, json.dumps(value, default=str))
            except Exception as e:
                logger.error(f"Redis set error: {e}")
        
        def delete(self, key: str):
            if not self.redis_client:
                return
            try:
                self.redis_client.delete(key)
            except Exception as e:
                logger.error(f"Redis delete error: {e}")
        
        def clear(self):
            if not self.redis_client:
                return
            try:
                self.redis_client.flushdb()
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
    
    # Try to create Redis cache, fall back to simple cache
    try:
        cache = RedisCache()
        if not cache.redis_client:
            cache = SimpleCache()
    except:
        cache = SimpleCache()

except ImportError:
    logger.info("Redis not available, using in-memory cache")
    cache = SimpleCache()

def get_cache_key(prefix: str, *args) -> str:
    """Generate cache key from prefix and arguments"""
    key_parts = [prefix] + [str(arg) for arg in args]
    return ":".join(key_parts)

def cached_fetch_news(topic: str, max_items: int = 3, cache_ttl: int = 300):
    """
    Cached version of fetch_news
    """
    from news import fetch_news
    
    cache_key = get_cache_key("news", topic, max_items)
    
    # Try to get from cache
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        logger.info(f"Cache hit for {cache_key}")
        return cached_data
    
    # Cache miss - fetch fresh data
    logger.info(f"Cache miss for {cache_key}, fetching fresh data")
    try:
        fresh_data = fetch_news(topic, max_items)
        # Cache the result
        cache.set(cache_key, fresh_data, cache_ttl)
        return fresh_data
    except Exception as e:
        logger.error(f"Error fetching news for {topic}: {e}")
        # Return empty list on error
        return []

def clear_news_cache():
    """Clear all news-related cache entries"""
    # For simple implementation, just clear entire cache
    # In production, you'd want more granular cache clearing
    cache.clear()
    logger.info("News cache cleared")
