from __future__ import annotations

from typing import Protocol

from app.config import TELEGRAM_SOURCE_CHANNELS
from app.models import NewsItem, SourceItem, SourceType, LogItem, LogLevel
from app.news_parser.sources.habr import HabrRssParser
from app.news_parser.sources.rbc import RbcRssParser
from app.news_parser.sources.vc import VcRssParser
from app.news_parser.sources.tproger import TprogerRssParser
from app.news_parser.sources.telegram_channels import TelegramChannelParser

from app.storage import get_log_storage
from app.services.log_service import LogService


class SiteParser(Protocol):
    async def parse(self, limit: int = 20) -> list[NewsItem]:
        ...


_PARSERS: dict[str, SiteParser] = {
    "habr": HabrRssParser(),
    "rbc": RbcRssParser(),
    "vc": VcRssParser(),
    "tproger": TprogerRssParser(),
}

for channel_username in TELEGRAM_SOURCE_CHANNELS:
    normalized = channel_username.strip().lstrip("@").lower()
    if not normalized:
        continue

    _PARSERS[f"tg:{normalized}"] = TelegramChannelParser(
        channel_username=normalized,
    )


def available_source_ids() -> list[str]:
    return sorted(_PARSERS.keys())


def available_sites() -> list[str]:
    """
    Backward-compatible alias.
    """
    return available_source_ids()


def available_source_items() -> list[SourceItem]:
    result: list[SourceItem] = []

    for key in available_source_ids():
        if key.startswith("tg:"):
            username = key.removeprefix("tg:")
            result.append(
                SourceItem(
                    id=key,
                    type=SourceType.TG,
                    name=f"@{username}",
                    url=f"https://t.me/{username}",
                    enabled=True,
                )
            )
            continue

        result.append(
            SourceItem(
                id=key,
                type=SourceType.SITE,
                name=key,
                url=None,
                enabled=True,
            )
        )
    return result


def _build_dynamic_parser(source_key: str) -> SiteParser | None:
    """
    Динамически создаёт parser для пользовательских источников,
    если они не входят во встроенный каталог.
    """
    if source_key.startswith("tg:"):
        username = source_key.removeprefix("tg:").strip().lstrip("@").lower()
        if not username:
            return None
        return TelegramChannelParser(channel_username=username)

    return None


async def collect_from_sites(sites: list[str], limit_per_site: int = 20) -> list[NewsItem]:
    """
    Собираем новости из указанных source keys.
    Если один источник упал - пропускаем его.
    Поддерживает:
    - встроенные источники из каталога
    - пользовательские TG-источники вида tg:<username>
    """
    result: list[NewsItem] = []

    log_service = LogService(get_log_storage())

    for key in sites:
        parser = _PARSERS.get(key)

        if parser is None:
            parser = _build_dynamic_parser(key)

        if parser is None:
            log_service.add_log(
                LogItem(
                    level=LogLevel.ERROR,
                    message=f"Parser not found for source={key}",
                    source="collect",
                    context={"source_key": key},
                )
            )
            continue

        try:
            items = await parser.parse(limit=limit_per_site)
            result.extend(items)

        except Exception as e:
            log_service.add_log(
                LogItem(
                    level=LogLevel.ERROR,
                    message=f"Failed to collect from source={key}: {str(e)}",
                    source="collect",
                    context={
                        "source_key": key,
                        "error": str(e),
                        "error_type": type(e).__name__,
                    },
                )
            )
            continue

    return result
