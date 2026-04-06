from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies.services import get_news_service
from app.api.errors import get_default_responses
from app.api.schemas import CollectSitesRequest, CollectSitesResponse
from app.services import NewsService

router = APIRouter(prefix="/collect")


@router.post(
    "/sites",
    response_model=CollectSitesResponse,
    summary="Collect news from sites",
    description="Collects news from selected sources.",
    responses={
        200: {"description": "News collected successfully"},
        **get_default_responses(),
    },
)
async def collect_sites(
        payload: CollectSitesRequest,
        service: NewsService = Depends(get_news_service),
) -> CollectSitesResponse:
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
