from __future__ import annotations

from app.config import STORAGE_BACKEND


#from app.storage.keywords import JsonlKeywordStorage
#from app.storage.news import JsonlNewsStorage
#from app.storage.posts import JsonlPostStorage
#from app.storage.sources import JsonlSourceStorage
#
#__all__ = [
#    "JsonlKeywordStorage",
#    "JsonlNewsStorage",
#    "JsonlPostStorage",
#    "JsonlSourceStorage"
#]
#

def get_storage_backend() -> str:
    """
    Возвращает активный backend хранения приложения.

    Допустимые значения:
    - jsonl
    - redis
    """
    backend = STORAGE_BACKEND.strip().lower()

    if backend not in {"jsonl", "redis"}:
        return "jsonl"

    return backend