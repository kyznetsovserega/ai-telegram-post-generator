from __future__ import annotations

from functools import lru_cache

import redis

from app.config import APP_REDIS_URL


@lru_cache(maxsize=1)
def get_redis_client() -> redis.Redis:
    """
    Возвращает singleton Redis client для storage-слоя приложения.
    """
    return redis.Redis.from_url(
        APP_REDIS_URL,
        decode_responses=True,
    )
