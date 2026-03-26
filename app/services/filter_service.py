from __future__ import annotations

from app.models import NewsItem, NewsStatus, KeywordType
from app.services.keyword_service import KeywordService


class FilterService:
    """MVP-фильтрация новостей для pipeline."""

    def __init__(self, keyword_service: KeywordService) -> None:
        self.keyword_service = keyword_service

    def apply_filter(self, items: list[NewsItem]) -> tuple[list[NewsItem], list[NewsItem]]:
        include_keywords = [
            item.value
            for item in self.keyword_service.list_by_type(KeywordType.INCLUDE)
        ]
        exclude_keywords = [
            item.value
            for item in self.keyword_service.list_by_type(KeywordType.EXCLUDE)
        ]

        filtered_items: list[NewsItem] = []
        dropped_items: list[NewsItem] = []
        seen_ids: set[str] = set()

        for item in items:
            if item.id in seen_ids:
                dropped_items.append(item.model_copy(update={"status": NewsStatus.DROPPED}))
                continue

            searchable_text = self._build_searchable_text(item)

            if not searchable_text:
                dropped_items.append(item.model_copy(update={"status": NewsStatus.DROPPED}))
                continue

            if self._contains_keyword(searchable_text, exclude_keywords):
                dropped_items.append(item.model_copy(update={"status": NewsStatus.DROPPED}))
                continue

            if include_keywords and not self._contains_keyword(searchable_text, include_keywords):
                dropped_items.append(item.model_copy(update={"status": NewsStatus.DROPPED}))
                continue

            seen_ids.add(item.id)
            filtered_items.append(item.model_copy(update={"status": NewsStatus.FILTERED}))

        return filtered_items, dropped_items

    def _build_searchable_text(self, item: NewsItem) -> str:
        parts = [
            item.title.strip(),
            item.summary.strip(),
            (item.raw_text or "").strip(),
        ]
        return self._normalize_text(" ".join(part for part in parts if part))

    def _normalize_text(self, value: str) -> str:
        return " ".join(value.lower().split())

    def _contains_keyword(self, searchable_text: str, keywords: list[str]) -> bool:
        return any(keyword.lower() in searchable_text for keyword in keywords)