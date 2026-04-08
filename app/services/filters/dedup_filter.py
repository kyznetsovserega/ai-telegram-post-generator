from __future__ import annotations

from app.models import NewsItem
from app.services.filters.base import FilterContext, FilterResult, FilterRule


class DedupFilter(FilterRule):
    """
    Дедупликация:
    1) in-memory (в рамках одного запуска filter stage)
    2) storage-level (через NewsService)

    - убрана прямая зависимость от RedisNewsStorage
    - фильтр больше не знает о Redis-ключах
    - storage-level dedup идёт через NewsService
    """

    def __init__(self, news_service) -> None:
        self.news_service = news_service

    def apply(self, item: NewsItem, context: FilterContext) -> FilterResult:
        # 1. In-memory dedup
        if item.id in context.seen_ids:
            return FilterResult.reject("duplicate_id")

        if item.content_hash and item.content_hash in context.seen_hashes:
            return FilterResult.reject("duplicate_content")

        # 2. Storage-level dedup
        if item.content_hash and self.news_service.exists_duplicate_content_hash(
                content_hash=item.content_hash,
                exclude_news_id=item.id,
        ):
            return FilterResult.reject("duplicate_content_storage")

        # сохраняем item в текущий batch-context
        context.seen_ids.add(item.id)

        if item.content_hash:
            context.seen_hashes.add(item.content_hash)

        return FilterResult.ok()
