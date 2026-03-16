from __future__ import annotations

from pathlib import Path

from app.models import NewsItem, NewsStatus
from app.news_parser.sites import available_sites, collect_from_sites
from app.storage.news import JsonlNewsStorage


class NewsService:
    """Сервис работы со сбором и хранением новостей."""

    def __init__(self, storage_path: str | Path = "data/news.jsonl") -> None:
        self.storage = JsonlNewsStorage(path=Path(storage_path))

    async def collect_from_sites(self, sites: list[str], limit_per_site: int) -> tuple[list[str], int, int]:
        supported = set(available_sites())
        requested_sites = [site for site in sites if site in supported]

        items = await collect_from_sites(
            sites=requested_sites,
            limit_per_site=limit_per_site,
        )

        normalized_items = [
            item.model_copy(update={"status": NewsStatus.NEW})
            for item in items
        ]

        saved = self.storage.save_many(normalized_items)

        return requested_sites, len(normalized_items), saved

    def get_by_id(self, news_id: str) -> NewsItem | None:
        return self.storage.get_by_id(news_id)

    def list_all(self) -> list[NewsItem]:
        return self.storage.list_all()

    def list_by_status(self, statuses: set[NewsStatus]) -> list[NewsItem]:
        return [
            item
            for item in self.storage.list_all()
            if item.status in statuses
        ]

    def replace_all(self, items: list[NewsItem]) -> None:
        self.storage.write_all(items)
