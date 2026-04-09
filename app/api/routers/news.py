from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_news_service
from app.api.errors import get_default_responses
from app.api.schemas import NewsItemResponse, NewsListResponse
from app.services.news_service import NewsService

router = APIRouter()


@router.get(
    "/news",
    response_model=NewsListResponse,
    summary="List news",
    description="Returns collected news items with their current processing status.",
    responses={
        200: {"description": "News returned successfully"},
        **get_default_responses(),
    },
)
async def list_news(
        limit: int = Query(
            default=50,
            ge=1,
            le=1000,
            description="Maximum number of news items to return",
        ),
        offset: int = Query(
            default=0,
            ge=0,
            description="Number of news items to skip",
        ),
        service: NewsService = Depends(get_news_service),
) -> NewsListResponse:
    items = service.list_paginated(limit=limit, offset=offset)
    total = service.count_all()

    response_items = [
        NewsItemResponse(
            id=item.id,
            title=item.title,
            summary=item.summary,
            url=item.url,
            source=item.source,
            status=item.status,
            published_at=item.published_at,
        )
        for item in items
    ]

    return NewsListResponse(
        items=response_items,
        total=total,
    )
