from __future__ import annotations

from app.models import NewsItem
from app.services.filters.base import FilterContext, FilterResult, FilterRule


class LanguageFilter(FilterRule):
    """
    Простой фильтр по языку.

    - если searchable_text пуст -> reject
    - если в тексте нет ни кириллицы, ни латиницы -> reject
    """

    def apply(self, item: NewsItem, context: FilterContext) -> FilterResult:
        text = context.searchable_text.strip()

        if not text:
            return FilterResult.reject("empty_searchable_text")

        has_cyrillic = any("а" <= ch <= "я" or "А" <= ch <= "Я" for ch in text)
        has_latin = any("a" <= ch <= "z" or "A" <= ch <= "Z" for ch in text)

        if not (has_cyrillic or has_latin):
            return FilterResult.reject("unsupported_language")

        return FilterResult.ok()
