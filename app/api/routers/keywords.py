from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.dependencies.services import get_keyword_service
from app.api.errors import get_default_responses, raise_api_error
from app.api.schemas import (
    ErrorResponse,
    KeywordCreateRequest,
    KeywordItemResponse,
    KeywordListResponse,
)
from app.models import KeywordType
from app.services import KeywordService

router = APIRouter()


@router.get(
    "/keywords",
    response_model=KeywordListResponse,
    summary="List keywords",
    description="Returns all filtering keywords (include/exclude).",
    responses={
        200: {"description": "Keywords returned successfully"},
        **get_default_responses(),
    },
)
async def list_keywords(
        service: KeywordService = Depends(get_keyword_service),
) -> KeywordListResponse:
    keywords = service.list_all()

    items = [
        KeywordItemResponse(
            value=keyword.value,
            type=keyword.type,
        )
        for keyword in keywords
    ]

    return KeywordListResponse(items=items, total=len(items))


@router.post(
    "/keywords",
    response_model=KeywordItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create keyword",
    description="Adds a keyword for filtering news (include or exclude).",
    responses={
        201: {"description": "Keyword created successfully"},
        **get_default_responses(),
    },
)
async def create_keyword(
        payload: KeywordCreateRequest,
        service: KeywordService = Depends(get_keyword_service),
) -> KeywordItemResponse:
    keyword = service.add_keyword(
        keyword_type=KeywordType(payload.type),
        value=payload.value,
    )

    return KeywordItemResponse(
        value=keyword.value,
        type=keyword.type,
    )


@router.delete(
    "/keywords/{keyword_type}/{value}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete keyword",
    description="Deletes a keyword by type (include/exclude) and value.",
    responses={
        204: {"description": "Keyword deleted successfully"},
        404: {
            "description": "Keyword not found",
            "model": ErrorResponse,
        },
        **get_default_responses(),
    },
)
async def delete_keyword(
        keyword_type: str,
        value: str,
        service: KeywordService = Depends(get_keyword_service),
) -> None:
    try:
        normalized_type = keyword_type.strip().lower()
        if normalized_type not in {"include", "exclude"}:
            raise_api_error(
                status_code=422,
                error_type="ValidationError",
                message="keyword_type must be include or exclude",
            )

        service.delete_keyword(
            keyword_type=KeywordType(normalized_type),
            value=value,
        )
    except LookupError as exc:
        raise_api_error(
            status_code=404,
            error_type="LookupError",
            message=str(exc),
        )
