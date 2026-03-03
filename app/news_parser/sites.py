from __future__ import annotations

from datetime import datetime, timezone
from typing import List

from app.models import NewsItem


def collect_site_news_stub() -> List[NewsItem]:
    now = datetime.now(timezone.utc)
    return [
        NewsItem(
            title="Stub news: FastAPI project started",
            url="https://example.com/news/1",
            summary="Базовый FastAPI сервис поднят и готов парсить источник.",
            source="stub",
            published_at=now,
        )
    ]
