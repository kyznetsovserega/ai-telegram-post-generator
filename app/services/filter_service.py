from __future__ import annotations

from app.models import NewsItem, NewsStatus, KeywordType, LogItem, LogLevel
from app.services.keyword_service import KeywordService
from app.storage.news import generate_content_hash


class FilterService:
    """Фильтрация новостей с логированием."""

    def __init__(self, keyword_service: KeywordService, log_service) -> None:
        self.keyword_service = keyword_service
        self.log_service = log_service

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
        seen_hashes: set[str] = set()

        for item in items:
            # --- считаем hash ОДИН РАЗ ---
            content_hash = generate_content_hash(item)

            item = item.model_copy(update={"content_hash": content_hash})

            # --- duplicate by ID ---
            if item.id in seen_ids:
                self._log_drop(item, "duplicate_id")
                dropped_items.append(item.model_copy(update={"status": NewsStatus.DROPPED}))
                continue

            searchable_text = self._build_searchable_text(item)

            if not searchable_text:
                self._log_drop(item, "empty_searchable_text")
                dropped_items.append(item.model_copy(update={"status": NewsStatus.DROPPED}))
                continue

            # --- duplicate by content ---
            if content_hash in seen_hashes:
                self._log_drop(item, "duplicate_content")
                dropped_items.append(item.model_copy(update={"status": NewsStatus.DROPPED}))
                continue

            # --- exclude ---
            if self._contains_keyword(searchable_text, exclude_keywords):
                self._log_drop(item, "excluded_by_keyword")
                dropped_items.append(item.model_copy(update={"status": NewsStatus.DROPPED}))
                continue

            # --- include ---
            if include_keywords and not self._contains_keyword(searchable_text, include_keywords):
                self._log_drop(item, "no_include_match")
                dropped_items.append(item.model_copy(update={"status": NewsStatus.DROPPED}))
                continue

            # --- OK ---
            seen_ids.add(item.id)
            seen_hashes.add(content_hash)

            filtered_items.append(item.model_copy(update={"status": NewsStatus.FILTERED}))

        return filtered_items, dropped_items

    def _log_drop(self, item: NewsItem, reason: str) -> None:
        self.log_service.add_log(
            LogItem(
                level=LogLevel.INFO,
                message="News item dropped",
                source="filter",
                context={
                    "reason": reason,
                    "news_id": item.id,
                    "source": item.source,
                },
            )
        )

    def _build_searchable_text(self, item: NewsItem) -> str:
        parts = [
            item.title.strip(),
            item.summary.strip(),
            (item.raw_text or "").strip(),
        ]
        return " ".join(part for part in parts if part).lower()

    def _contains_keyword(self, searchable_text: str, keywords: list[str]) -> bool:
        return any(keyword.lower() in searchable_text for keyword in keywords)
