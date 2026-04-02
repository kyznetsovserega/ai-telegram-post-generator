from __future__ import annotations

from celery import shared_task

from app.storage.redis_client import get_redis_client


@shared_task(name="app.tasks.cleanup.cleanup_indexes")
def cleanup_indexes() -> dict[str, int]:
    """
    Удаляет битые ссылки в индексах Redis:
    - news:ids
    - posts:ids
    - logs:ids
    """

    redis = get_redis_client()

    removed = {
        "news": 0,
        "posts": 0,
        "logs": 0,
    }

    news_ids = redis.smembers("news:ids")
    for news_id in news_ids:
        if not redis.exists(f"news:item:{news_id}"):
            redis.srem("news:ids", news_id)
            removed["news"] += 1

    post_ids = redis.smembers("posts:ids")
    for post_id in post_ids:
        if not redis.exists(f"posts:item:{post_id}"):
            redis.srem("posts:ids", post_id)
            removed["posts"] += 1

    log_ids = redis.zrange("logs:ids", 0, -1)
    for log_id in log_ids:
        if not redis.exists(f"logs:item:{log_id}"):
            redis.zrem("logs:ids", log_id)
            removed["logs"] += 1

    return removed
