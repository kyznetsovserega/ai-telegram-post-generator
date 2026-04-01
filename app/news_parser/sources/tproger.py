from __future__ import annotations

from dataclasses import dataclass

from app.models import NewsItem
from app.news_parser.sources.rss_common import (
    build_rss_items,
    fetch_rss_xml,
)

TPROGER_RSS_URL = "https://tproger.ru/feed/"


@dataclass(frozen=True)
class TprogerRssParser:
    timeout_s: float = 15.0

    async def parse(self, limit: int = 20) -> list[NewsItem]:
        xml = await fetch_rss_xml(
            TPROGER_RSS_URL,
            timeout_s=self.timeout_s,
        )
        return build_rss_items(
            source="tproger",
            xml=xml,
            limit=limit,
        )
