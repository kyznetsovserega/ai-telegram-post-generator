from __future__ import annotations

from app.models import NewsItem,NewsStatus


class FilterService:
    """Минимальная фильтрация новостей для pipeline."""

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
                dropped_items.append(item.model_copy(update={"status": NewsStatus.DROPPED}))
                continue

            title = item.title.strip()
            summary = item.summary.strip()
            raw_text = (item.raw_text or "").strip()

            if not title and not summary and not raw_text:
                dropped_items.append(item.model_copy(update={"status": NewsStatus.DROPPED}))
                continue

            seen_ids.add(item.id)
            filtered_items.append(
                item.model_copy(update={"status": NewsStatus.FILTERED})
            )

        return filtered_items, dropped_items
