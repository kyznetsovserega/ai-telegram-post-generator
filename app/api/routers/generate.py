from __future__ import annotations

from fastapi import APIRouter, Depends

from app.api.dependencies.services import get_generation_service
from app.api.errors import get_ai_responses, raise_for_ai_error
from app.api.schemas import (
    GenerateFromNewsRequest,
    GenerateFromNewsResponse,
    GenerateRequest,
    GenerateResponse,
)
from app.services import GenerationService

router = APIRouter()


@router.post(
    "/generate/",
    response_model=GenerateResponse,
    summary="Generate post from text",
    description="Generates a Telegram-ready post using LLM based on input text.",
    responses={
        200: {"description": "Post generated successfully"},
        **get_ai_responses(),
    },
)
async def generate_post(
        payload: GenerateRequest,
        service: GenerationService = Depends(get_generation_service),
) -> GenerateResponse:
    try:
        generated_text = await service.generate_from_text(payload.text)
        return GenerateResponse(generated_text=generated_text)
    except Exception as exc:
        raise_for_ai_error(exc)


@router.post(
    "/generate/from-news",
    response_model=GenerateFromNewsResponse,
    summary="Generate post from news",
    description="Generates a post based on a stored news item.",
    responses={
        200: {"description": "Post generated from news successfully"},
        **get_ai_responses(),
    },
)
async def generate_post_from_news(
        payload: GenerateFromNewsRequest,
        service: GenerationService = Depends(get_generation_service),
) -> GenerateFromNewsResponse:
    try:
        post_item = await service.generate_from_news(payload.news_id)

        return GenerateFromNewsResponse(
            id=post_item.id,
            news_id=post_item.news_id,
            generated_text=post_item.generated_text,
            status=post_item.status,
            created_at=post_item.created_at,
            published_at=post_item.published_at,
            source=post_item.source,
            provider=post_item.provider,
            external_message_id=post_item.external_message_id,
        )
    except Exception as exc:
        raise_for_ai_error(exc)
