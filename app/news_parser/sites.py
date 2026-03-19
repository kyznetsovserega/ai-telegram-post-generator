from __future__ import annotations

from typing import Protocol

from app.config import TELEGRAM_SOURCE_CHANNELS
from app.models import NewsItem
from app.news_parser.sources.habr import HabrRssParser
from app.news_parser.sources.rbc import RbcRssParser
from app.news_parser.sources.vc import VcRssParser
from app.news_parser.sources.tproger import TprogerRssParser
from app.news_parser.sources.telegram_channels import TelegramChannelParser


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


def available_sites() -> list[str]:
    return sorted(_PARSERS.keys())


async def collect_from_sites(sites: list[str], limit_per_site: int = 20) -> list[NewsItem]:
    """
    Собираем новости из указанных source keys.
    Если один источник упал - пропускаем его.
    """
    result: list[NewsItem] = []

    for key in sites:
        parser = _PARSERS.get(key)
        if parser is None:
            continue

        try:
            items = await parser.parse(limit=limit_per_site)
            result.extend(items)
        except Exception:
            continue

    return result
