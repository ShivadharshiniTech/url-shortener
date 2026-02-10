import re
from typing import Optional

# Base62 character set
BASE62 = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"

def encode_id(id: int) -> str:
    """Convert database ID to Base62 short code"""
    if id == 0:
        return BASE62[0]
    
    result = ""
    while id > 0:
        result = BASE62[id % 62] + result
        id //= 62
    return result

def decode_base62(short_code: str) -> int:
    """Convert Base62 short code back to database ID"""
    result = 0
    for char in short_code:
        result = result * 62 + BASE62.index(char)
    return result

def is_valid_url(url: str) -> bool:
    """Basic URL validation"""
    url_pattern = re.compile(
        r'^https?://'  # http:// or https://
        r'(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|'  # domain...
        r'localhost|'  # localhost...
        r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})'  # ...or ip
        r'(?::\d+)?'  # optional port
        r'(?:/?|[/?]\S+)$', re.IGNORECASE)
    return url_pattern.match(url) is not None

def normalize_url(url: str) -> str:
    """Normalize URL by adding protocol if missing"""
    if not url.startswith(('http://', 'https://')):
        return f'https://{url}'
    return url

def is_valid_alias(alias: str) -> bool:
    """Check if custom alias is valid (alphanumeric, 3-20 chars)"""
    if not alias:
        return False
    return bool(re.match(r'^[a-zA-Z0-9_-]{3,20}$', alias))