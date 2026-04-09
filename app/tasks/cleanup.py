from __future__ import annotations

from celery import shared_task

from app.storage.redis_client import get_redis_client


@shared_task(name="app.tasks.cleanup.cleanup_indexes")
def cleanup_indexes() -> dict[str, int]:
    """
    Удаляет битые ссылки в индексах Redis:
    - news:ids
    - news:published_at
    - news:content_hash:*
    - posts:ids
    - posts:created_at
    - posts:by_news_id:*
    - logs:ids
    """

    redis = get_redis_client()

    removed = {
        "news": 0,
        "news_published_index": 0,
        "news_hash_links": 0,
        "posts": 0,
        "posts_created_index": 0,
        "posts_news_index": 0,
        "logs": 0,
    }

    # NEWS IDS
    news_ids = redis.smembers("news:ids")
    for news_id in news_ids:
        if not redis.exists(f"news:item:{news_id}"):
            redis.srem("news:ids", news_id)
            removed["news"] += 1

    # NEWS PUBLISHED INDEX
    news_index_ids = redis.zrange("news:published_at", 0, -1)
    for news_id in news_index_ids:
        if not redis.exists(f"news:item:{news_id}"):
            redis.zrem("news:published_at", news_id)
            removed["news_published_index"] += 1

    # NEWS HASH INDEX
    for key in redis.scan_iter("news:content_hash:*"):
        news_id = redis.get(key)
        if not news_id or not redis.exists(f"news:item:{news_id}"):
            redis.delete(key)
            removed["news_hash_links"] += 1

    # POSTS IDS
    post_ids = redis.smembers("posts:ids")
    for post_id in post_ids:
        if not redis.exists(f"posts:item:{post_id}"):
            redis.srem("posts:ids", post_id)
            removed["posts"] += 1

    # POSTS CREATED INDEX
    post_index_ids = redis.zrange("posts:created_at", 0, -1)
    for post_id in post_index_ids:
        if not redis.exists(f"posts:item:{post_id}"):
            redis.zrem("posts:created_at", post_id)
            removed["posts_created_index"] += 1

    # POSTS NEWS INDEX
    for key in redis.scan_iter("posts:by_news_id:*"):
        post_id = redis.get(key)
        if not post_id or not redis.exists(f"posts:item:{post_id}"):
            redis.delete(key)
            removed["posts_news_index"] += 1

    # LOGS IDS
    log_ids = redis.zrange("logs:ids", 0, -1)
    for log_id in log_ids:
        if not redis.exists(f"logs:item:{log_id}"):
            redis.zrem("logs:ids", log_id)
            removed["logs"] += 1

    return removed
