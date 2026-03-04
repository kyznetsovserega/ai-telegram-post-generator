from __future__ import annotations

from typing import List, Dict, Protocol

from app.models import NewsItem
from app.news_parser.sources.habr import HabrRssParser


class SiteParser(Protocol):
    async def parse(self, limit: int = 20) -> List[NewsItem]: ...


_PARSERS: Dict[str, object] = {
    "habr": HabrRssParser(),
}


def available_sites() -> List[str]:
    return sorted(_PARSERS.keys())


async def collect_from_sites(sites: List[str], limit_per_site: int = 20) -> List[NewsItem]:
    """
    MVP: собираем новости из указанных site keys.
    Если один источник упал - пропускаем его.
    """
    result: List[NewsItem] = []

    for key in sites:
        parser = _PARSERS.get(key)
        if parser is None:
            continue

        try:
            items = await parser.parse(limit=limit_per_site)  # type: ignore[attr-defined]
            result.extend(items)
        except Exception:
            continue

    return result
