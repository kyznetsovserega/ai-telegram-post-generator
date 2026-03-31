from __future__ import annotations

from app.models import NewsItem
from app.services.filters.base import FilterContext, FilterResult, FilterRule


class DedupFilter(FilterRule):
    """
    In-memory дедупликация внутри одного запуска filter stage.

    - не заменяет storage-level dedup
    - не лезет в Redis / storage
    """

    def apply(self, item: NewsItem, context: FilterContext) -> FilterResult:
        if item.id in context.seen_ids:
            return FilterResult.reject("duplicate_id")

        if item.content_hash and item.content_hash in context.seen_hashes:
            return FilterResult.reject("duplicate_content")

        context.seen_ids.add(item.id)

        if item.content_hash:
            context.seen_hashes.add(item.content_hash)

        return FilterResult.ok()
