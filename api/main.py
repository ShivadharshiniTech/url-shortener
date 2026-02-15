from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, text
from pydantic import BaseModel, HttpUrl
from typing import Optional
import os

from api.database import get_db, engine, Base
from api.models import Url, Click
from api.utils import encode_id, decode_base62, is_valid_url, normalize_url, is_valid_alias
from api.cache import cache
from api.rate_limit import rate_limiter

app = FastAPI(title="URL Shortener", description="Production-grade URL shortener")

# Templates setup
templates = Jinja2Templates(directory="templates")

# Pydantic models
class ShortenRequest(BaseModel):
    url: str
    custom_alias: Optional[str] = None

class ShortenResponse(BaseModel):
    short_url: str
    original_url: str
    short_code: str

@app.on_event("startup")
async def startup():
    """Create database tables on startup with error handling"""
    try:
        print("🔄 Attempting database connection...")
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("✅ Database tables created successfully")
    except Exception as e:
        print(f"⚠️ Database startup error: {e}")
        print("App will continue running, but database operations may fail")
        # Don't crash the app - let it start anyway

# Health check endpoints (must come before /{short_code})
@app.get("/health")
async def health_check():
    """Health check endpoint for monitoring"""
    return {
        "status": "healthy",
        "service": "url-shortener",
        "version": "1.0.0"
    }

# Root and page routes (must come before /{short_code})
@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with URL shortening form"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.get("/analytics", response_class=HTMLResponse)
async def analytics_page(request: Request):
    """Analytics dashboard page"""
    return templates.TemplateResponse("analytics.html", {"request": request})

@app.get("/api/health/db")
async def database_health(db: AsyncSession = Depends(get_db)):
    """Database health check"""
    try:
        await db.execute(text("SELECT 1"))
        return {"status": "healthy", "database": "connected"}
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Database unhealthy: {str(e)}")

@app.get("/api/health/redis")
async def redis_health():
    """Redis health check"""
    if not cache.enabled:
        return {"status": "disabled", "redis": "not configured"}
    
    is_healthy = await cache.health_check()
    if is_healthy:
        return {"status": "healthy", "redis": "connected"}
    else:
        return {"status": "unhealthy", "redis": "connection failed"}

# Admin endpoints (must come before /{short_code})
@app.get("/api/admin/urls")
async def list_urls(limit: int = 50, db: AsyncSession = Depends(get_db)):
    """List all URLs (development only)"""
    result = await db.execute(
        select(Url).order_by(Url.created_at.desc()).limit(limit)
    )
    urls = result.scalars().all()
    
    return [
        {
            "id": url.id,
            "short_code": url.short_code,
            "original_url": url.original_url,
            "custom_alias": url.custom_alias,
            "click_count": url.click_count,
            "created_at": url.created_at,
            "is_active": url.is_active
        }
        for url in urls
    ]

@app.get("/api/admin/clicks")
async def list_clicks(limit: int = 100, db: AsyncSession = Depends(get_db)):
    """List recent clicks (development only)"""
    result = await db.execute(
        select(Click).order_by(Click.clicked_at.desc()).limit(limit)
    )
    clicks = result.scalars().all()
    
    return [
        {
            "id": click.id,
            "url_id": click.url_id,
            "ip_address": click.ip_address,
            "user_agent": click.user_agent,
            "referer": click.referer,
            "clicked_at": click.clicked_at
        }
        for click in clicks
    ]

@app.post("/api/shorten", response_model=ShortenResponse)
async def shorten_url(
    request_data: ShortenRequest,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Create a shortened URL"""
    # Rate limiting: 10 requests per minute
    await rate_limiter.check_rate_limit(request, limit=10, window=60)
    
    # Validate and normalize URL
    if not is_valid_url(request_data.url):
        normalized_url = normalize_url(request_data.url)
        if not is_valid_url(normalized_url):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        request_data.url = normalized_url
    
    # Check custom alias if provided
    if request_data.custom_alias:
        if not is_valid_alias(request_data.custom_alias):
            raise HTTPException(
                status_code=400, 
                detail="Custom alias must be 3-20 characters (letters, numbers, _, -)"
            )
        
        # Check if alias already exists
        existing = await db.execute(
            select(Url).where(Url.custom_alias == request_data.custom_alias)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Custom alias already exists")
    
    # Create new URL record
    new_url = Url(
        original_url=request_data.url,
        custom_alias=request_data.custom_alias
    )
    
    db.add(new_url)
    await db.commit()
    await db.refresh(new_url)
    
    # Generate response
    short_code = request_data.custom_alias or new_url.short_code
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    
    return ShortenResponse(
        short_url=f"{base_url}/{short_code}",
        original_url=request_data.url,
        short_code=short_code
    )

@app.get("/{short_code}")
async def redirect_url(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Redirect to original URL and track click"""
    # Try Redis cache first (for popular URLs only)
    cache_key = f"url:{short_code}"
    cached_url = await cache.get(cache_key)
    
    if cached_url:
        # Cache hit - redirect immediately and track click in background
        click = Click(
            url_id=0,  # We'll update this later if needed
            ip_address=request.client.host,
            user_agent=request.headers.get("user-agent"),
            referer=request.headers.get("referer")
        )
        # Note: For cached URLs, we skip detailed click tracking to save DB calls
        return RedirectResponse(url=cached_url, status_code=301)
    
    # Cache miss - query database
    url_record = None
    
    # Try to find by custom alias first
    result = await db.execute(
        select(Url).where(Url.custom_alias == short_code, Url.is_active == True)
    )
    url_record = result.scalar_one_or_none()
    
    # If not found by alias, try decoding as Base62 ID
    if not url_record:
        try:
            url_id = decode_base62(short_code)
            result = await db.execute(
                select(Url).where(Url.id == url_id, Url.is_active == True)
            )
            url_record = result.scalar_one_or_none()
        except (ValueError, IndexError):
            pass
    
    if not url_record:
        raise HTTPException(status_code=404, detail="Short URL not found")
    
    # Track click
    click = Click(
        url_id=url_record.id,
        ip_address=request.client.host,
        user_agent=request.headers.get("user-agent"),
        referer=request.headers.get("referer")
    )
    db.add(click)
    
    # Update click count
    await db.execute(
        update(Url)
        .where(Url.id == url_record.id)
        .values(click_count=Url.click_count + 1)
    )
    
    await db.commit()
    
    # Cache popular URLs (10+ clicks) for 1 hour
    if url_record.click_count >= 10:
        await cache.set(cache_key, url_record.original_url, ttl=3600)
    
    return RedirectResponse(url=url_record.original_url, status_code=301)

@app.get("/api/stats/{short_code}")
async def get_stats(
    short_code: str,
    db: AsyncSession = Depends(get_db)
):
    """Get click statistics for a short URL"""
    url_record = None
    
    # Try custom alias first
    result = await db.execute(
        select(Url).where(Url.custom_alias == short_code)
    )
    url_record = result.scalar_one_or_none()
    
    # Try Base62 decode
    if not url_record:
        try:
            url_id = decode_base62(short_code)
            result = await db.execute(
                select(Url).where(Url.id == url_id)
            )
            url_record = result.scalar_one_or_none()
        except (ValueError, IndexError):
            pass
    
    if not url_record:
        raise HTTPException(status_code=404, detail="Short URL not found")
    
    return {
        "short_code": short_code,
        "original_url": url_record.original_url,
        "click_count": url_record.click_count,
        "created_at": url_record.created_at,
        "is_active": url_record.is_active
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)