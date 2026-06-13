import redis.asyncio as redis
from core import settings

redis_config = settings.redis
url = redis_config.get_url()
redis_client = redis.from_url(url, decode_responses=True)
