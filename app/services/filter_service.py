from __future__ import annotations

from app.config import FILTER_EXCLUDE_KEYWORDS, FILTER_INCLUDE_KEYWORDS
from app.models import NewsItem, NewsStatus


class FilterService:
    """MVP-фильтрация новостей для pipeline."""

    def apply_filter(self, items: list[NewsItem]) -> tuple[list[NewsItem], list[NewsItem]]:
        """
        Возвращает два списка:
        - filtered_items: новости, пригодные для генерации
        - dropped_items: новости, отброшенные фильтром
        """
        filtered_items: list[NewsItem] = []
        dropped_items: list[NewsItem] = []
        seen_ids: set[str] = set()

        for item in items:
            if item.id in seen_ids:
                dropped_items.append(
                    item.model_copy(update={"status": NewsStatus.DROPPED})
                )
                continue

            searchable_text = self._build_searchable_text(item)

            if not searchable_text:
                dropped_items.append(
                    item.model_copy(update={"status": NewsStatus.DROPPED})
                )
                continue

            if self._contains_exclude_keyword(searchable_text):
                dropped_items.append(
                    item.model_copy(update={"status": NewsStatus.DROPPED})
                )
                continue

            if FILTER_INCLUDE_KEYWORDS and not self._contains_include_keyword(
                    searchable_text
            ):
                dropped_items.append(
                    item.model_copy(update={"status": NewsStatus.DROPPED})
                )
                continue

            seen_ids.add(item.id)
            filtered_items.append(
                item.model_copy(update={"status": NewsStatus.FILTERED})
            )

        return filtered_items, dropped_items

    def _build_searchable_text(self, item: NewsItem) -> str:
        parts = [
            item.title.strip(),
            item.summary.strip(),
            (item.raw_text or "").strip(),
        ]
        joined_text = " ".join(part for part in parts if part)
        return self._normalize_text(joined_text)

    def _normalize_text(self, value: str) -> str:
        return " ".join(value.lower().split())

    def _contains_include_keyword(self, searchable_text: str) -> bool:
        return any(keyword.lower() in searchable_text for keyword in FILTER_INCLUDE_KEYWORDS)

    def _contains_exclude_keyword(self, searchable_text: str) -> bool:
        return any(keyword.lower() in searchable_text for keyword in FILTER_EXCLUDE_KEYWORDS)
