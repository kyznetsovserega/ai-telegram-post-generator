from __future__ import annotations

from collections.abc import Callable

from app.models import NewsItem, NewsStatus

from app.services.source_service import SourceService

NewsCollector = Callable[..., list[NewsItem]]
AvailableSitesProvider = Callable[[], list[str]]


class NewsService:
    """Сервис работы со сбором и хранением новостей."""

    def __init__(
            self,
            storage,
            source_service: SourceService,
            collector,
            available_sites_provider,
    ):
        self.storage = storage
        self.source_service = source_service
        self.collector = collector
        self.available_sites_provider = available_sites_provider

    async def collect_from_sites(self, sites: list[str], limit_per_site: int) -> tuple[list[str], int, int]:
        supported_sites = set(self.available_sites_provider())
        requested_sites = [site for site in sites if site in supported_sites]

        available_sources = {source.id: source for source in self.source_service.list_all()}
        enabled_sites = [
            site
            for site in requested_sites
            if available_sources.get(site) is not None and available_sources[site].enabled
        ]

        items = await self.collector(
            sites=enabled_sites,
            limit_per_site=limit_per_site,
        )

        normalized_items = [
            item.model_copy(update={"status": NewsStatus.NEW})
            for item in items
        ]

        saved = self.storage.save_many(normalized_items)

        return enabled_sites, len(normalized_items), saved

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
