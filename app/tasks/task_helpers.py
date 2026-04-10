from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

from app.core.container import get_container
from app.storage.redis_client import get_redis_client


def get_enabled_source_ids() -> list[str]:
    """
    Возвращает все enabled source ids из storage.
    """
    container = get_container()
    source_service = container.source_service

    return [
        source.id
        for source in source_service.list_all()
        if source.enabled
    ]


def run_async(coro: Coroutine[Any, Any, Any]) -> Any:
    """
    Единая sync -> async граница для Celery.
    Переход sync/async локализован в task layer.
    """
    return asyncio.run(coro)


def acquire_lock(key: str, ttl: int = 120) -> bool:
    """
    Простой Redis lock:
    SET key NX EX ttl
    """
    redis = get_redis_client()

    return bool(
        redis.set(
            name=key,
            value="1",
            nx=True,
            ex=ttl,
        )
    )


def release_lock(key: str) -> None:
    """
    Снимает Redis lock.
    """
    redis = get_redis_client()
    redis.delete(key)
