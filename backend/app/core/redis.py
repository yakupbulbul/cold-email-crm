import redis
from app.core.config import settings

def get_redis_client() -> redis.Redis:
    """Connects to Redis using settings."""
    return redis.from_url(settings.REDIS_URL, decode_responses=True)
