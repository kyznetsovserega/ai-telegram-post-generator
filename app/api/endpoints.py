from __future__ import annotations

from typing import NoReturn

from fastapi import APIRouter, HTTPException, status

from app.ai.errors import (
    AiGenerationError,
    AiProviderResponseError,
    AiRateLimitError,
    AiTemporaryUnavailableError,
)
from app.api.schemas import (
    CollectSitesRequest,
    CollectSitesResponse,
    GenerateFromNewsRequest,
    GenerateFromNewsResponse,
    GenerateRequest,
    GenerateResponse,
    KeywordCreateRequest,
    KeywordItemResponse,
    KeywordListResponse,
    PostHistoryItemResponse,
    PostHistoryListResponse,
    SourceItemResponse,
    SourceListResponse,
    SourceUpdateRequest,
)
from app.models import KeywordType
from app.services import GenerationService, NewsService, PostService, KeywordService
from app.services.source_service import SourceService

router = APIRouter()


def _raise_for_ai_error(exc: Exception) -> NoReturn:
    if isinstance(exc, RuntimeError):
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if isinstance(exc, LookupError):
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    if isinstance(exc, AiRateLimitError):
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    if isinstance(exc, AiTemporaryUnavailableError):
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if isinstance(exc, AiProviderResponseError):
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if isinstance(exc, ValueError):
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    if isinstance(exc, AiGenerationError):
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    raise HTTPException(
        status_code=502,
        detail=f"LLM integration error: {type(exc).__name__}: {exc}",
    ) from exc


@router.get("/sources", response_model=SourceListResponse)
async def list_sources() -> SourceListResponse:
    service = SourceService()
    sources = service.list_all()

    items = [
        SourceItemResponse(
            id=source.id,
            type=source.type,
            name=source.name,
            url=source.url,
            enabled=source.enabled,
        )
        for source in sources
    ]

    return SourceListResponse(items=items, total=len(items))


@router.patch("/sources/{source_id}", response_model=SourceItemResponse)
async def update_source(source_id: str, payload: SourceUpdateRequest) -> SourceItemResponse:
    try:
        service = SourceService()
        source = service.set_enabled(source_id=source_id, enabled=payload.enabled)

        return SourceItemResponse(
            id=source.id,
            type=source.type,
            name=source.name,
            url=source.url,
            enabled=source.enabled,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


# GET /api/keywords
@router.get("/keywords", response_model=KeywordListResponse)
async def list_keywords() -> KeywordListResponse:
    service = KeywordService()
    keywords = service.list_all()

    items = [
        KeywordItemResponse(
            value=keyword.value,
            type=keyword.type,
        )
        for keyword in keywords
    ]

    return KeywordListResponse(items=items, total=len(items))


# POST /api/keywords
@router.post("/keywords", response_model=KeywordItemResponse, status_code=status.HTTP_201_CREATED)
async def create_keyword(payload: KeywordCreateRequest) -> KeywordItemResponse:
    service = KeywordService()
    keyword = service.add_keyword(
        keyword_type=KeywordType(payload.type),
        value=payload.value,
    )

    return KeywordItemResponse(
        value=keyword.value,
        type=keyword.type,
    )


# DELETE /api/keywords/{keyword_type}/{value}
@router.delete("/keywords/{keyword_type}/{value}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(keyword_type: str, value: str) -> None:
    try:
        normalized_type = keyword_type.strip().lower()
        if normalized_type not in {"include", "exclude"}:
            raise HTTPException(status_code=422, detail="keyword_type must be include or exclude")

        service = KeywordService()
        service.delete_keyword(
            keyword_type=KeywordType(normalized_type),
            value=value,
        )
    except LookupError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


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


@router.post("/generate/", response_model=GenerateResponse)
async def generate_post(payload: GenerateRequest) -> GenerateResponse:
    try:
        service = GenerationService()
        generated_text = await service.generate_from_text(payload.text)
        return GenerateResponse(generated_text=generated_text)
    except Exception as exc:
        _raise_for_ai_error(exc)


@router.post(
    "/generate/from-news",
    response_model=GenerateFromNewsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_post_from_news(payload: GenerateFromNewsRequest) -> GenerateFromNewsResponse:
    try:
        service = GenerationService()
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
        _raise_for_ai_error(exc)
