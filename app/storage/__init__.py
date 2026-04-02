from __future__ import annotations

from pathlib import Path

from app.config import STORAGE_BACKEND
from app.storage.keywords import JsonlKeywordStorage, RedisKeywordStorage
from app.storage.logs import JsonlLogStorage, RedisLogStorage, LogStorageProtocol
from app.storage.news import RedisNewsStorage, JsonlNewsStorage
from app.storage.posts import JsonlPostStorage, RedisPostStorage
from app.storage.sources import JsonlSourceStorage, RedisSourceStorage


def get_storage_backend() -> str:
    """
    Возвращает активный backend хранения приложения.

    Допустимые значения:
    - jsonl
    - redis
    """
    backend = STORAGE_BACKEND.strip().lower()

    if backend not in {"jsonl", "redis"}:
        raise ValueError(f"Unsupported storage backend: {backend}")

    return backend


def get_news_storage():
    backend = get_storage_backend()

    if backend == "redis":
        return RedisNewsStorage()

    return JsonlNewsStorage(Path("data/news.jsonl"))


def get_post_storage():
    backend = get_storage_backend()

    if backend == "redis":
        return RedisPostStorage()

    return JsonlPostStorage()


def get_source_storage():
    backend = get_storage_backend()

    if backend == "redis":
        return RedisSourceStorage()

    return JsonlSourceStorage()


def get_keyword_storage():
    backend = get_storage_backend()

    if backend == "redis":
        return RedisKeywordStorage()

    return JsonlKeywordStorage()

def get_log_storage() -> LogStorageProtocol:
    """Возвращает реализацию log storage по активному backend."""
    backend = get_storage_backend()

    if backend == "redis":
        return RedisLogStorage()

    return JsonlLogStorage()
