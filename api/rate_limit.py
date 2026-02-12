from fastapi import HTTPException, Request
from api.cache import cache
import time

class RateLimiter:
    def __init__(self):
        self.enabled = cache.enabled
    
    async def check_rate_limit(self, request: Request, limit: int = 10, window: int = 60):
        """
        Simple rate limiting using Redis
        Args:
            request: FastAPI request object
            limit: Number of requests allowed (default: 10)
            window: Time window in seconds (default: 60)
        """
        if not self.enabled:
            return True  # No rate limiting if Redis is disabled
        
        # Use IP address as identifier
        client_ip = request.client.host
        key = f"rate_limit:{client_ip}"
        
        try:
            # Get current count
            current_count = await cache.increment(key, 1)
            
            # Handle case where increment returns None (Redis error)
            if current_count is None:
                return True  # Allow request if Redis fails
            
            if current_count == 1:
                # First request in window, set expiration
                await cache.expire(key, window)
            
            if current_count > limit:
                raise HTTPException(
                    status_code=429,
                    detail=f"Rate limit exceeded. Max {limit} requests per {window} seconds."
                )
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            print(f"⚠️ Rate limiting error: {e}")
            return True  # Allow request if rate limiting fails

# Global rate limiter instance
rate_limiter = RateLimiter()