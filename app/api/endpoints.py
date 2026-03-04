from __future__ import annotations

from pathlib import Path
from typing import List

from fastapi import APIRouter
from pydantic import BaseModel, Field

from app.news_parser.sites import available_sites, collect_from_sites
from app.storage.news_storage import JsonlNewsStorage

router = APIRouter()


class CollectSitesRequest(BaseModel):
    sites: List[str] = Field(default_factory=lambda: ["habr"])
    limit_per_site: int = 20


class CollectSitesResponse(BaseModel):
    requested_sites: List[str]
    collected: int
    saved: int


@router.post("/collect/sites", response_model=CollectSitesResponse)
async def collect_sites(payload: CollectSitesRequest) -> CollectSitesResponse:
    storage = JsonlNewsStorage(path=Path("date/news.jsonl"))

    supported = set(available_sites())
    sites = [s for s in payload.sites if s in supported]

    items = await collect_from_sites(sites=sites, limit_per_site=payload.limit_per_site)
    saved = storage.append_many(items)

    return CollectSitesResponse(
        requested_sites=sites,
        collected=len(items),
        saved=saved,
    )
