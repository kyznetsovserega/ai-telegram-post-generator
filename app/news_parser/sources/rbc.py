from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.models import NewsItem
from app.news_parser.sources.rss_common import build_rss_items

RBC_RSS_URL = "https://rssexport.rbc.ru/rbcnews/news/30/full.rss"


@dataclass(frozen=True)
class RbcRssParser:
    timeout_s: float = 15.0
    user_agent: str = "ai-telegram-post-generator/0.1 (+https://example.local)"

    async def fetch(self) -> str:
        async with httpx.AsyncClient(
                timeout=self.timeout_s,
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
        ) as client:
            response = await client.get(RBC_RSS_URL)
            response.raise_for_status()
            return response.text

    async def parse(self, limit: int = 20) -> list[NewsItem]:
        xml = await self.fetch()
        return build_rss_items(
            source="rbc",
            xml=xml,
            limit=limit,
        )
