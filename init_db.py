#!/usr/bin/env python3
"""
Database initialization script for Neon PostgreSQL
"""
import asyncio
import os
from dotenv import load_dotenv
from api.database import engine, Base
from api.models import Url, Click

async def init_database():
    """Initialize database tables"""
    load_dotenv()
    
    print("🔗 Initializing URL Shortener Database...")
    print(f"📊 Database URL: {os.getenv('DATABASE_URL', 'Not set')[:50]}...")
    
    try:
        # Create all tables
        async with engine.begin() as conn:
            print("📋 Creating database tables...")
            await conn.run_sync(Base.metadata.create_all)
        
        print("✅ Database initialized successfully!")
        print("🚀 You can now run: python run.py")
        
    except Exception as e:
        print(f"❌ Database initialization failed: {e}")
        print("\n🔧 Troubleshooting:")
        print("1. Check your DATABASE_URL in .env file")
        print("2. Ensure your Neon database is active")
        print("3. Verify network connectivity")
        return False
    
    finally:
        await engine.dispose()
    
    return True

async def test_connection():
    """Test database connection"""
    try:
        async with engine.begin() as conn:
            result = await conn.execute("SELECT 1")
            print("✅ Database connection successful!")
            return True
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        return False
    finally:
        await engine.dispose()

if __name__ == "__main__":
    print("🔗 URL Shortener - Database Setup")
    print("=" * 40)
    
    # Load environment
    load_dotenv()
    
    if not os.getenv("DATABASE_URL"):
        print("❌ DATABASE_URL not found in .env file")
        print("📝 Please copy .env.example to .env and add your Neon connection string")
        exit(1)
    
    # Run initialization
    asyncio.run(init_database())