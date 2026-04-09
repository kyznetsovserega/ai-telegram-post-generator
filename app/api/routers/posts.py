from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_post_service
from app.api.errors import get_default_responses
from app.api.schemas import PostHistoryItemResponse, PostHistoryListResponse
from app.services import PostService

router = APIRouter()


@router.get(
    "/posts",
    response_model=PostHistoryListResponse,
    summary="List generated posts",
    description="Returns generated posts with their publication status.",
    responses={
        200: {"description": "Posts retrieved successfully"},
        **get_default_responses(),
    },
)
async def list_generated_posts(
        limit: int = Query(
            default=50,
            ge=1,
            le=1000,
            description="Maximum number of posts to return",
        ),
        offset: int = Query(
            default=0,
            ge=0,
            description="Number of posts to skip",
        ),
        service: PostService = Depends(get_post_service),
) -> PostHistoryListResponse:
    posts = service.list_paginated(limit=limit, offset=offset)
    total = service.count_all()

    items = [
        PostHistoryItemResponse(
            id=post.id,
            news_id=post.news_id,
            generated_text=post.generated_text,
            status=post.status,
            created_at=post.created_at,
            published_at=post.published_at,
            source=post.source,
            provider=post.provider,
            external_message_id=post.external_message_id,
        )
        for post in posts
    ]

    return PostHistoryListResponse(items=items, total=total)
