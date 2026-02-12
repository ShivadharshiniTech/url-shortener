# URL Shortener

A production-grade URL shortener built with FastAPI and PostgreSQL.

## Features

- **ID-based Base62 encoding** (zero collisions)
- **Custom aliases** support
- **Click tracking** and analytics
- **URL validation** and normalization
- **Async database** operations
- **Clean web interface**

## Architecture

- **Backend**: FastAPI with async SQLAlchemy
- **Database**: Neon PostgreSQL (Free tier: 512MB RAM, 10GB storage)
- **URL Generation**: Base62 encoding from auto-increment IDs
- **Frontend**: Jinja2 templates with TailwindCSS

## Why Neon PostgreSQL?

- **Free tier**: 512MB RAM, 10GB storage (perfect for URL shortener)
- **Built-in connection pooling**: No need for external pgbouncer
- **Serverless**: Scales to zero when not in use
- **Global**: Low latency worldwide
- **No maintenance**: Automatic backups and updates

## Why Upstash Redis?

- **Free tier**: 10k commands/day, 256MB storage
- **Global edge**: Low latency worldwide
- **Smart caching**: Only popular URLs (10+ clicks) are cached
- **Graceful fallback**: App works without Redis
- **Rate limiting**: Prevent abuse with Redis counters

## Quick Start

1. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

2. **Set up Neon Database**:
   ```bash
   # 1. Go to https://neon.tech and create free account
   # 2. Create new project
   # 3. Copy connection string from dashboard
   
   # Copy environment file
   cp .env.example .env
   
   # Edit .env and replace DATABASE_URL with your Neon connection string
   # Example: postgresql+asyncpg://user:pass@ep-name-123.us-east-2.aws.neon.tech/neondb?sslmode=require
   ```

3. **Set up Redis (Optional but Recommended)**:
   ```bash
   # 1. Go to https://upstash.com and create free account
   # 2. Create new Redis database
   # 3. Copy connection URL from dashboard
   
   # Add REDIS_URL to your .env file
   # Example: redis://default:password@region-redis.upstash.io:6379
   ```

3. **Initialize database**:
   ```bash
   python init_db.py
   ```

4. **Run the application**:
   ```bash
   python run.py
   ```

4. **Open browser**: http://localhost:8000

## API Endpoints

### Shorten URL
```bash
POST /api/shorten
Content-Type: application/json

{
  "url": "https://example.com",
  "custom_alias": "my-link"  # optional
}
```

### Redirect
```bash
GET /{short_code}
# Returns 301 redirect to original URL
```

### Get Statistics
```bash
GET /api/stats/{short_code}
# Returns click count and metadata
```

## Database Schema

### URLs Table
- `id` (Primary Key, Auto-increment)
- `original_url` (String, Required)
- `custom_alias` (String, Optional, Unique)
- `created_at` (Timestamp)
- `is_active` (Boolean)
- `click_count` (Integer)

### Clicks Table
- `id` (Primary Key)
- `url_id` (Foreign Key)
- `ip_address` (String)
- `user_agent` (String)
- `referer` (String)
- `clicked_at` (Timestamp)

## URL Generation Logic

```python
# ID-based Base62 encoding (no collisions)
def encode_id(id: int) -> str:
    BASE62 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"
    # Convert ID to Base62 string
```

## Production Deployment

- Use environment variables for configuration
- Enable connection pooling with `pgbouncer=true`
- Set up proper logging and monitoring
- Configure HTTPS and security headers

## Development

```bash
# Install in development mode
pip install -e .

# Run with auto-reload
python run.py

# Database migrations (if using Alembic)
alembic revision --autogenerate -m "Initial migration"
alembic upgrade head
```