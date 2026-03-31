from __future__ import annotations

from app.models import NewsItem
from app.services.filters.base import FilterContext, FilterResult, FilterRule


class KeywordFilter(FilterRule):
    """
    Фильтр по include / exclude keywords.
    """

    def apply(self, item: NewsItem, context: FilterContext) -> FilterResult:
        searchable_text = context.searchable_text

        if self._contains_keyword(searchable_text, context.exclude_keywords):
            return FilterResult.reject("excluded_by_keyword")

        if context.include_keywords and not self._contains_keyword(
                searchable_text,
                context.include_keywords,
        ):
            return FilterResult.reject("no_include_match")

        return FilterResult.ok()

    @staticmethod
    def _contains_keyword(searchable_text: str, keywords: list[str]) -> bool:
        return any(keyword.lower() in searchable_text for keyword in keywords)
