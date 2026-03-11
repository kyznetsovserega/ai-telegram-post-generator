from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, status

from app import config
from app.ai.errors import (
    AiGenerationError,
    AiProviderResponseError,
    AiRateLimitError,
    AiTemporaryUnavailableError,
)
from app.ai.factory import build_text_generation_client
from app.ai.generator import PostGenerator
from app.api.schemas import (
    CollectSitesRequest,
    CollectSitesResponse,
    GenerateFromNewsRequest,
    GenerateFromNewsResponse,
    GenerateRequest,
    GenerateResponse,
)
from app.models import PostItem
from app.news_parser.sites import available_sites, collect_from_sites
from app.storage.news import JsonlNewsStorage
from app.storage.posts import JsonlPostStorage

router = APIRouter()


@router.post("/collect/sites", response_model=CollectSitesResponse)
async def collect_sites(payload: CollectSitesRequest) -> CollectSitesResponse:
    storage = JsonlNewsStorage(path=Path("data/news.jsonl"))

    supported = set(available_sites())
    sites = [s for s in payload.sites if s in supported]

    items = await collect_from_sites(sites=sites, limit_per_site=payload.limit_per_site)
    saved = storage.save_many(items)

    return CollectSitesResponse(
        requested_sites=sites,
        collected=len(items),
        saved=saved,
    )


@router.post("/generate/", response_model=GenerateResponse)
async def generate_post(payload: GenerateRequest) -> GenerateResponse:
    provider = config.LLM_PROVIDER.lower()

    if provider == "openai" and not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    if provider == "gemini" and not config.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")

    try:
        client = build_text_generation_client()
        generator = PostGenerator(client=client)
        post = await generator.generate_from_text(payload.text)
    except AiRateLimitError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AiTemporaryUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AiProviderResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AiGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM integration error: {type(exc).__name__}: {exc}",
        ) from exc

    return GenerateResponse(generated_text=post.text)


@router.post(
    "/generate/from-news",
    response_model=GenerateFromNewsResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_post_from_news(payload: GenerateFromNewsRequest, ) -> GenerateFromNewsResponse:
    provider = config.LLM_PROVIDER.lower()

    if provider == "openai" and not config.OPENAI_API_KEY:
        raise HTTPException(status_code=500, detail="OPENAI_API_KEY is not configured")

    if provider == "gemini" and not config.GEMINI_API_KEY:
        raise HTTPException(status_code=500, detail="GEMINI_API_KEY is not configured")

    news_storage = JsonlNewsStorage(path=Path("data/news.jsonl"))
    post_storage = JsonlPostStorage(Path("data/posts.jsonl"))

    news_item = news_storage.get_by_id(payload.news_id)
    if news_item is None:
        raise HTTPException(
            status_code=404,
            detail=f"News item with id='{payload.news_id}' not found",
        )

    # Проверяем существующий пост
    existing_post = post_storage.get_by_news_id(news_item.id)

    if existing_post is not None:
        return GenerateFromNewsResponse(
            id=existing_post.id,
            news_id=existing_post.news_id,
            generated_text=existing_post.generated_text,
            status=existing_post.status,
            created_at=existing_post.created_at,
            published_at=existing_post.published_at,
            source=existing_post.source,
            provider=existing_post.provider,
        )

    try:
        client = build_text_generation_client()
        generator = PostGenerator(client=client)
        generated_post = await generator.generate_from_news(news_item)
    except AiRateLimitError as exc:
        raise HTTPException(status_code=503, detail=str(exc)) from exc
    except AiTemporaryUnavailableError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AiProviderResponseError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except AiGenerationError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM integration error: {type(exc).__name__}: {exc}",
        ) from exc

    post_item = PostItem(
        id=str(uuid4()),
        news_id=news_item.id,
        generated_text=generated_post.text,
        status="generated",
        created_at=datetime.now(timezone.utc),
        published_at=None,
        source=news_item.source,
        provider=provider,
    )

    post_storage.save(post_item)

    return GenerateFromNewsResponse(
        id=post_item.id,
        news_id=post_item.news_id,
        generated_text=post_item.generated_text,
        status=post_item.status,
        created_at=post_item.created_at,
        published_at=post_item.published_at,
        source=post_item.source,
        provider=post_item.provider,
    )
