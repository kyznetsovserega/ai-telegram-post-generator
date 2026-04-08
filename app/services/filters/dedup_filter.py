from __future__ import annotations

from app.models import NewsItem
from app.services.filters.base import FilterContext, FilterResult, FilterRule
from app.storage.news import RedisNewsStorage


class DedupFilter(FilterRule):
    """
    Дедупликация:
    1) In-memory (в рамках одного запуска)
    2) Storage-level (Redis)

    - добавлена проверка Redis (storage-level dedup)
    """

    def __init__(self) -> None:
        # подключаем storage
        self.storage = RedisNewsStorage()

    def apply(self, item: NewsItem, context: FilterContext) -> FilterResult:
        # 1. In-memory dedup
        if item.id in context.seen_ids:
            return FilterResult.reject("duplicate_id")

        if item.content_hash and item.content_hash in context.seen_hashes:
            return FilterResult.reject("duplicate_content")

        # 2. Storage-level dedup
        if item.content_hash:
            hash_key = self.storage._hash_key(item.content_hash)  # используем ту же логику ключей
            if self.storage.redis.exists(hash_key):
                return FilterResult.reject("duplicate_content_storage")

        # сохраняем в контекст
        context.seen_ids.add(item.id)

        if item.content_hash:
            context.seen_hashes.add(item.content_hash)

        return FilterResult.ok()
