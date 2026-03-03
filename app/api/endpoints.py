from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter

from app.news_parser.sites import collect_site_news_stub
from app.storage.news_storage import JsonNewsStorage

router = APIRouter()

storage = JsonNewsStorage(Path("data/news.jsonl"))


@router.post("/collect/sites")
async def collect_sites():
    items = collect_site_news_stub()
    saved = storage.append_many(items)
    return {"saved": saved}
