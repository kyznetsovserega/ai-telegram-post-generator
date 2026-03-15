from __future__ import annotations

from app.models import NewsItem


class FilterService:
    """Минимальная фильтрация новостей для pipeline."""

    def filter_news(self, items: list[NewsItem]) -> list[NewsItem]:
        result: list[NewsItem] = []
        seen_ids: set[str] = set()

        for item in items:
            if item.id in seen_ids:
                continue

            title = item.title.strip()
            summary = item.summary.strip()
            raw_text = (item.raw_text or "").strip()

            if not title and not summary and not raw_text:
                continue

            seen_ids.add(item.id)
            result.append(item)

        return result
