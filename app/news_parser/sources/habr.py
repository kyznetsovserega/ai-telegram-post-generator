from __future__ import annotations

import hashlib
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import List

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.models import NewsItem

HABR_RSS_URL = "https://habr.com/ru/rss/all/all/?fl=ru"


def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text(" ", strip=True)
    return " ".join(text.split())


def _to_datetime(entry: dict) -> datetime:
    """ Пытаемся достать дату публикации из RSS. """
    tm = entry.get("published_parsed") or entry.get("updated_parsed")
    if tm:
        # tm — time.struct_time
        return datetime(
            tm.tm_year,
            tm.tm_mon,
            tm.tm_mday,
            tm.tm_hour,
            tm.tm_min,
            tm.tm_sec,
            tzinfo=timezone.utc,
        )
    return datetime.now(tz=timezone.utc)

def _build_news_id(title: str, url: str | None, published_at: datetime) -> str:
    """
    Создание стабильного идентификатора новостей
    для дедупликации и хранения.
    """
    base = url or f"{title}|{published_at.isoformat()}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()

@dataclass(frozen=True)
class HabrRssParser:
    timeout_s: float = 15.0
    user_agent: str = "ai-telegram-post-generator/0.1 (+https://example.local)"

    async def fetch(self) -> str:
        async with httpx.AsyncClient(
                timeout=self.timeout_s,
                headers={"User-Agent": self.user_agent},
                follow_redirects=True,
        ) as client:
            r = await client.get(HABR_RSS_URL)
            r.raise_for_status()
            return r.text

    async def parse(self, limit: int = 20) -> List[NewsItem]:
        xml = await self.fetch()
        feed = feedparser.parse(xml)

        items: List[NewsItem] = []

        for entry in (feed.entries or [])[:limit]:
            title = (entry.get("title") or "").strip()
            url = (entry.get("link") or "").strip()

            raw_summary = entry.get("summary") or entry.get("description") or ""
            summary = _strip_html(raw_summary)

            if not title:
                continue

            published_at = _to_datetime(entry)
            news_id = _build_news_id(title=title, url=url or None, published_at=published_at)

            items.append(
                NewsItem(
                    id=news_id,
                    title=title,
                    url=url or None,
                    summary=summary,
                    source="habr",
                    published_at=published_at,
                )
            )

        return items
