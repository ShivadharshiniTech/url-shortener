import os
import json
from typing import Optional
from dotenv import load_dotenv

# Force reload environment variables
load_dotenv(override=True)

class RedisCache:
    def __init__(self):
        # Force reload env vars in case they changed
        load_dotenv(override=True)
        
        self.rest_url = os.getenv("UPSTASH_REDIS_REST_URL")
        self.rest_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
        self.client = None
        self.enabled = bool(self.rest_url and self.rest_token)
        
        print(f"🔴 Redis REST URL found: {bool(self.rest_url)}")
        print(f"🔴 Redis REST Token found: {bool(self.rest_token)}")
        if self.rest_url:
            print(f"🔴 REST URL: {self.rest_url}")
        
        if self.enabled:
            try:
                from upstash_redis import Redis
                self.client = Redis(url=self.rest_url, token=self.rest_token)
                print(f"✅ Upstash Redis REST client created for: {self.rest_url}")
            except Exception as e:
                print(f"⚠️ Redis REST client setup failed: {e}")
                self.enabled = False
        else:
            print("🔴 Redis disabled - missing UPSTASH_REDIS_REST_URL or UPSTASH_REDIS_REST_TOKEN")
    
    async def get(self, key: str) -> Optional[str]:
        """Get value from cache"""
        if not self.enabled or not self.client:
            return None
        
        try:
            result = self.client.get(key)
            return result if result is not None else None
        except Exception as e:
            print(f"⚠️ Redis GET error: {e}")
            return None
    
    async def set(self, key: str, value: str, ttl: int = 3600) -> bool:
        """Set value in cache with TTL (default 1 hour)"""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.setex(key, ttl, value)
            return True
        except Exception as e:
            print(f"⚠️ Redis SET error: {e}")
            return False
    
    async def delete(self, key: str) -> bool:
        """Delete key from cache"""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.delete(key)
            return True
        except Exception as e:
            print(f"⚠️ Redis DELETE error: {e}")
            return False
    
    async def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """Increment counter (for rate limiting)"""
        if not self.enabled or not self.client:
            return None
        
        try:
            return self.client.incrby(key, amount)
        except Exception as e:
            print(f"⚠️ Redis INCR error: {e}")
            return None
    
    async def expire(self, key: str, ttl: int) -> bool:
        """Set TTL on existing key"""
        if not self.enabled or not self.client:
            return False
        
        try:
            self.client.expire(key, ttl)
            return True
        except Exception as e:
            print(f"⚠️ Redis EXPIRE error: {e}")
            return False
    
    async def health_check(self) -> bool:
        """Check if Redis is healthy"""
        if not self.enabled or not self.client:
            return False
        
        try:
            result = self.client.ping()
            return result == "PONG"
        except Exception:
            return False

# Global cache instance
cache = RedisCache()