"""Redis-backed response caching utility."""

import json
import logging
from typing import Any

from app.core.redis import get_redis_client

logger = logging.getLogger(__name__)

_PREFIX = "crm:cache:"


def cache_get(key: str) -> Any | None:
    """Get cached JSON value by key. Returns None on miss or error."""
    try:
        client = get_redis_client()
        raw = client.get(f"{_PREFIX}{key}")
        if raw is None:
            return None
        return json.loads(raw)
    except Exception as e:
        logger.debug(f"Cache get error for {key}: {e}")
        return None


def cache_set(key: str, data: Any, ttl: int = 300) -> None:
    """Store JSON data with TTL (seconds). Failures are silent."""
    try:
        client = get_redis_client()
        client.setex(f"{_PREFIX}{key}", ttl, json.dumps(data, default=str))
    except Exception as e:
        logger.debug(f"Cache set error for {key}: {e}")


def cache_invalidate(prefix: str) -> int:
    """Delete all cache keys matching prefix. Returns count deleted."""
    try:
        client = get_redis_client()
        keys = client.keys(f"{_PREFIX}{prefix}*")
        if keys:
            return client.delete(*keys)
        return 0
    except Exception as e:
        logger.debug(f"Cache invalidate error for {prefix}: {e}")
        return 0
