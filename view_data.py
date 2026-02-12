#!/usr/bin/env python3
"""
Quick script to view database data
Usage: python view_data.py
"""
import asyncio
from api.database import AsyncSessionLocal
from api.models import Url, Click
from sqlalchemy import select

async def view_urls():
    """View all URLs in the database"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Url).order_by(Url.created_at.desc()).limit(20)
        )
        urls = result.scalars().all()
        
        print("\n=== URLS ===")
        print(f"{'ID':<5} {'Short Code':<12} {'Original URL':<50} {'Clicks':<8} {'Created'}")
        print("-" * 90)
        
        for url in urls:
            print(f"{url.id:<5} {url.short_code:<12} {url.original_url[:47]+'...' if len(url.original_url) > 50 else url.original_url:<50} {url.click_count:<8} {url.created_at.strftime('%Y-%m-%d %H:%M')}")

async def view_clicks():
    """View recent clicks"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            select(Click).order_by(Click.created_at.desc()).limit(20)
        )
        clicks = result.scalars().all()
        
        print("\n=== RECENT CLICKS ===")
        print(f"{'ID':<5} {'URL ID':<8} {'IP Address':<15} {'Created'}")
        print("-" * 50)
        
        for click in clicks:
            print(f"{click.id:<5} {click.url_id:<8} {click.ip_address:<15} {click.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

async def main():
    await view_urls()
    await view_clicks()

if __name__ == "__main__":
    asyncio.run(main())