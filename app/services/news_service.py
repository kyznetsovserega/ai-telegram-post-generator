from __future__ import annotations

from pathlib import Path

from app.models import NewsItem
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
        saved = self.storage.save_many(items)

        return requested_sites, len(items), saved

    def get_by_id(self, news_id: str) -> NewsItem | None:
        return self.storage.get_by_id(news_id)
