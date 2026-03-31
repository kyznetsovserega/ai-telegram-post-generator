from __future__ import annotations

from collections.abc import Awaitable, Callable

from app.models import LogItem, LogLevel, NewsItem, NewsStatus
from app.services.log_service import LogService
from app.services.source_service import SourceService

NewsCollector = Callable[..., Awaitable[list[NewsItem]]]
AvailableSitesProvider = Callable[[], list[str]]


class NewsService:
    """Сервис работы со сбором и хранением новостей."""

    def __init__(
            self,
            storage,
            source_service: SourceService,
            collector: NewsCollector,
            available_sites_provider: AvailableSitesProvider,
            log_service: LogService,
    ) -> None:
        self.storage = storage
        self.source_service = source_service
        self.collector = collector
        self.available_sites_provider = available_sites_provider
        self.log_service = log_service

    async def collect_from_sites(
            self,
            sites: list[str],
            limit_per_site: int,
    ) -> tuple[list[str], int, int]:
        """
        Собирает новости только по поддерживаемым и enabled источникам.
        """
        available_sources = {
            source.id: source
            for source in self.source_service.list_all()
        }

        catalog_sites = set(self.available_sites_provider())
        supported_sites = catalog_sites | set(available_sources.keys())

        unknown_sites = [site for site in sites if site not in supported_sites]
        for site in unknown_sites:
            self.log_service.add_log(
                LogItem(
                    level=LogLevel.ERROR,
                    message=f"Unsupported source requested: {site}",
                    source="collect",
                    context={"source_key": site},
                )
            )

        requested_sites = [site for site in sites if site in supported_sites]

        enabled_sites = [
            site
            for site in requested_sites
            if available_sources.get(site) is not None and available_sources[site].enabled
        ]

        if not enabled_sites:
            self.log_service.add_log(
                LogItem(
                    level=LogLevel.WARNING,
                    message="No enabled sources available for collection",
                    source="collect",
                    context={"requested_sites": requested_sites},
                )
            )
            return [], 0, 0

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

    def update_items(self, items: list[NewsItem]) -> None:
        self.storage.write_all(items)
