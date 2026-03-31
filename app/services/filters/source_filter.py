from __future__ import annotations

from app.models import NewsItem
from app.services.filters.base import FilterContext, FilterResult, FilterRule


class SourceFilter(FilterRule):
    """
    Фильтр по источнику.

    Если enabled_source_ids не передан,
    фильтр не блокирует новости.
    """

    def apply(self, item: NewsItem, context: FilterContext) -> FilterResult:
        if context.enabled_source_ids is None:
            return FilterResult.ok()

        if item.source not in context.enabled_source_ids:
            return FilterResult.reject("source_disabled")

        return FilterResult.ok()
