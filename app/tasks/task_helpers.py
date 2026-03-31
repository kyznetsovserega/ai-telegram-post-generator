from __future__ import annotations

import asyncio
from collections.abc import Coroutine
from typing import Any

from app.core.container import get_container


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
    переход sync/async локализован в task layer
    """
    return asyncio.run(coro)
