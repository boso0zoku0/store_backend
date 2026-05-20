from redis import Redis

from core import settings

redis_config = settings.redis.redis_url
redis_client = Redis.from_url(redis_config, decode_responses=True)
