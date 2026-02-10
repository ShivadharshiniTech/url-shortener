from fastapi import FastAPI, HTTPException, Depends, Request, Form
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from pydantic import BaseModel, HttpUrl
from typing import Optional
import os

from api.database import get_db, engine, Base
from api.models import Url, Click
from api.utils import encode_id, decode_base62, is_valid_url, normalize_url, is_valid_alias

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
    """Create database tables on startup"""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Home page with URL shortening form"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/api/shorten", response_model=ShortenResponse)
async def shorten_url(
    request: ShortenRequest,
    db: AsyncSession = Depends(get_db)
):
    """Create a shortened URL"""
    # Validate and normalize URL
    if not is_valid_url(request.url):
        normalized_url = normalize_url(request.url)
        if not is_valid_url(normalized_url):
            raise HTTPException(status_code=400, detail="Invalid URL format")
        request.url = normalized_url
    
    # Check custom alias if provided
    if request.custom_alias:
        if not is_valid_alias(request.custom_alias):
            raise HTTPException(
                status_code=400, 
                detail="Custom alias must be 3-20 characters (letters, numbers, _, -)"
            )
        
        # Check if alias already exists
        existing = await db.execute(
            select(Url).where(Url.custom_alias == request.custom_alias)
        )
        if existing.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Custom alias already exists")
    
    # Create new URL record
    new_url = Url(
        original_url=request.url,
        custom_alias=request.custom_alias
    )
    
    db.add(new_url)
    await db.commit()
    await db.refresh(new_url)
    
    # Generate response
    short_code = request.custom_alias or new_url.short_code
    base_url = os.getenv("BASE_URL", "http://localhost:8000")
    
    return ShortenResponse(
        short_url=f"{base_url}/{short_code}",
        original_url=request.url,
        short_code=short_code
    )

@app.get("/{short_code}")
async def redirect_url(
    short_code: str,
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Redirect to original URL and track click"""
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
    
    # Track click (async, don't wait)
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