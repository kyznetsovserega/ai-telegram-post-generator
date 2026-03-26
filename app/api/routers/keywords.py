from __future__ import annotations

from fastapi import APIRouter, status

from app.api.errors import raise_api_error
from app.api.schemas import (
    KeywordCreateRequest,
    KeywordItemResponse,
    KeywordListResponse,
)
from app.models import KeywordType
from app.services import KeywordService

router = APIRouter()


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


@router.delete("/keywords/{keyword_type}/{value}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_keyword(keyword_type: str, value: str) -> None:
    try:
        normalized_type = keyword_type.strip().lower()
        if normalized_type not in {"include", "exclude"}:
            raise_api_error(
                status_code=422,
                error_type="ValidationError",
                message="keyword_type must be include or exclude",
            )

        service = KeywordService()
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
