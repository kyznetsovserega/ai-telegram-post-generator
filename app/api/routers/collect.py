from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import CollectSitesRequest, CollectSitesResponse
from app.services import NewsService

router = APIRouter()


@router.post("/collect/sites", response_model=CollectSitesResponse)
async def collect_sites(payload: CollectSitesRequest) -> CollectSitesResponse:
    service = NewsService()

    requested_sites = payload.sites

    processed_sites, collected, saved = await service.collect_from_sites(
        sites=payload.sites,
        limit_per_site=payload.limit_per_site,
    )

    return CollectSitesResponse(
        requested_sites=requested_sites,
        processed_sites=processed_sites,
        collected=collected,
        saved=saved,
    )
