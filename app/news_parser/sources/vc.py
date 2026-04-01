from __future__ import annotations

from dataclasses import dataclass

from app.models import NewsItem
from app.news_parser.sources.rss_common import (
    build_rss_items,
    fetch_rss_xml,
)

VC_RSS_URL = "https://vc.ru/rss/all"


@dataclass(frozen=True)
class VcRssParser:
    timeout_s: float = 15.0

    async def parse(self, limit: int = 20) -> list[NewsItem]:
        xml = await fetch_rss_xml(
            VC_RSS_URL,
            timeout_s=self.timeout_s,
        )
        return build_rss_items(
            source="vc",
            xml=xml,
            limit=limit,
        )
