from __future__ import annotations

import hashlib
from datetime import datetime, timezone
from typing import Any

import feedparser
import httpx
from bs4 import BeautifulSoup

from app.models import NewsItem

DEFAULT_TIMEOUT = 15.0
DEFAULT_USER_AGENT = "ai-telegram-post-generator/0.1"


# --- HTTP helper ---
async def fetch_rss_xml(
        url: str,
        *,
        timeout_s: float = DEFAULT_TIMEOUT,
        user_agent: str = DEFAULT_USER_AGENT,
) -> str:
    async with httpx.AsyncClient(
            timeout=timeout_s,
            headers={"User-Agent": user_agent},
            follow_redirects=True,
    ) as client:
        response = await client.get(url)
        response.raise_for_status()
        return response.text


# --- utils ---
def _strip_html(html: str) -> str:
    soup = BeautifulSoup(html or "", "html.parser")
    text = soup.get_text(" ", strip=True)
    return " ".join(text.split())


def entry_to_datetime(entry: dict[str, Any]) -> datetime:
    """Извлекает дату публикации из RSS entry."""
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


def build_news_id(
        *,
        source: str,
        title: str,
        url: str | None,
        published_at: datetime,
        raw_text: str = "",
) -> str:
    """Создание стабильного ID новости (для дедупликации)."""
    base = url or f"{source}|{title}|{published_at.isoformat()}|{raw_text[:200]}"
    return hashlib.sha256(base.encode("utf-8")).hexdigest()


# --- main builder ---
def build_rss_items(
        *,
        source: str,
        xml: str,
        limit: int,
) -> list[NewsItem]:
    feed = feedparser.parse(xml)
    items: list[NewsItem] = []

    for entry in (feed.entries or [])[:limit]:
        title = (entry.get("title") or "").strip()
        url = (entry.get("link") or "").strip()

        raw_summary = entry.get("summary") or entry.get("description") or ""
        summary = _strip_html(raw_summary)

        if not title:
            continue

        published_at = entry_to_datetime(entry)

        news_id = build_news_id(
            source=source,
            title=title,
            url=url or None,
            published_at=published_at,
            raw_text=summary,
        )

        items.append(
            NewsItem(
                id=news_id,
                title=title,
                url=url or None,
                summary=summary,
                source=source,
                published_at=published_at,
            )
        )
    return items
