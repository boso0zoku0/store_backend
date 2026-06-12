from redis import Redis

from core import settings

redis_config = settings.redis
url = redis_config.get_url()
redis_client = Redis.from_url(url, decode_responses=True)
