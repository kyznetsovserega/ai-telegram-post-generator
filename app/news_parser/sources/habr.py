from __future__ import annotations

from dataclasses import dataclass

from app.models import NewsItem
from app.news_parser.sources.rss_common import (
    build_rss_items,
    fetch_rss_xml,
)

HABR_RSS_URL = "https://habr.com/ru/rss/all/all/?fl=ru"


@dataclass(frozen=True)
class HabrRssParser:
    timeout_s: float = 15.0

    async def parse(self, limit: int = 20) -> list[NewsItem]:
        xml = await fetch_rss_xml(
            HABR_RSS_URL,
            timeout_s=self.timeout_s,
        )
        return build_rss_items(
            source="habr",
            xml=xml,
            limit=limit,
        )
