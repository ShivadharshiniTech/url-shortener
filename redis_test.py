from upstash_redis import Redis
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test():
    rest_url = os.getenv("UPSTASH_REDIS_REST_URL")
    rest_token = os.getenv("UPSTASH_REDIS_REST_TOKEN")
    
    print(f"🔴 REST URL: {rest_url}")
    print(f"🔴 REST Token: {rest_token[:20]}..." if rest_token else "None")
    
    if not rest_url or not rest_token:
        print("❌ Missing REST URL or Token!")
        return
    
    try:
        redis = Redis(url=rest_url, token=rest_token)
        print("✅ Redis REST client created successfully")
        
        # Test ping
        result = redis.ping()
        print(f"✅ Redis ping successful: {result}")
        
        # Test set/get
        redis.set("test_key", "test_value", ex=60)
        value = redis.get("test_key")
        print(f"✅ Set/Get test successful: {value}")
        
    except Exception as e:
        print(f"❌ Redis REST connection failed: {type(e).__name__}: {e}")

test()
