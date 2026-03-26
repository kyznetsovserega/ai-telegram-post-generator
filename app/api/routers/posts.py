from __future__ import annotations

from fastapi import APIRouter

from app.api.schemas import PostHistoryItemResponse, PostHistoryListResponse
from app.services import PostService

router = APIRouter()


@router.get("/posts", response_model=PostHistoryListResponse)
async def list_generated_posts() -> PostHistoryListResponse:
    service = PostService()
    posts = service.list_all()

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

    return PostHistoryListResponse(items=items, total=len(items))

