from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies.services import get_news_service
from app.api.schemas import NewsItemResponse, NewsListResponse
from app.services.news_service import NewsService

router = APIRouter()


@router.get("/news", response_model=NewsListResponse)
async def list_news(
        service: NewsService = Depends(get_news_service),
) -> NewsListResponse:
    items = service.list_all()

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
        total=len(response_items),
    )
