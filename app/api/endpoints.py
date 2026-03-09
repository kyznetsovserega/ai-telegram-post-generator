from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, HTTPException
from openai import APIConnectionError, APIStatusError, APITimeoutError, RateLimitError

from app import config
from app.ai.factory import build_text_generation_client
from app.ai.generator import PostGenerator
from app.api.schemas import (
    CollectSitesRequest,
    CollectSitesResponse,
    GenerateRequest,
    GenerateResponse,
)
from app.news_parser.sites import available_sites, collect_from_sites
from app.storage.news_storage import JsonlNewsStorage

router = APIRouter()


@router.post("/collect/sites", response_model=CollectSitesResponse)
async def collect_sites(payload: CollectSitesRequest) -> CollectSitesResponse:
    storage = JsonlNewsStorage(path=Path("data/news.jsonl"))

    supported = set(available_sites())
    sites = [s for s in payload.sites if s in supported]

    items = await collect_from_sites(sites=sites, limit_per_site=payload.limit_per_site)
    saved = storage.append_many(items)

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
    except RateLimitError as exc:
        raise HTTPException(
            status_code=503,
            detail="OpenAI quota/rate limit error. Check billing, project budget, and API limits.",
        ) from exc
    except (APITimeoutError, APIConnectionError) as exc:
        raise HTTPException(
            status_code=502,
            detail="OpenAI is temporarily unavailable",
        ) from exc
    except APIStatusError as exc:
        raise HTTPException(
            status_code=502,
            detail=f"OpenAI API returned status error: {exc.status_code}",
        ) from exc
    except ValueError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(
            status_code=502,
            detail=f"LLM integration error: {type(exc).__name__}: {exc}",
        ) from exc

    return GenerateResponse(generated_text=post.text)
