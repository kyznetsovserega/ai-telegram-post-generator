from __future__ import annotations

from fastapi import APIRouter, status

from app.api.errors import raise_api_error
from app.api.schemas import (
    SourceCreateRequest,
    SourceItemResponse,
    SourceListResponse,
    SourceUpdateRequest,
)
from app.models import SourceItem, SourceType
from app.services.source_service import SourceService

router = APIRouter()


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


@router.post("/sources", response_model=SourceItemResponse, status_code=status.HTTP_201_CREATED)
async def create_source(payload: SourceCreateRequest) -> SourceItemResponse:
    try:
        service = SourceService()
        source = service.create_source(
            SourceItem(
                id=payload.id,
                type=SourceType(payload.type),
                name=payload.name,
                url=payload.url,
                enabled=payload.enabled,
            )
        )

        return SourceItemResponse(
            id=source.id,
            type=source.type,
            name=source.name,
            url=source.url,
            enabled=source.enabled,
        )
    except ValueError as exc:
        raise_api_error(
            status_code=400,
            error_type="ValueError",
            message=str(exc),
        )


@router.patch("/sources/{source_id}", response_model=SourceItemResponse)
async def update_source(source_id: str, payload: SourceUpdateRequest) -> SourceItemResponse:
    try:
        service = SourceService()
        source = service.update_source(
            source_id=source_id,
            name=payload.name,
            url=payload.url,
            enabled=payload.enabled,
        )

        return SourceItemResponse(
            id=source.id,
            type=source.type,
            name=source.name,
            url=source.url,
            enabled=source.enabled,
        )
    except LookupError as exc:
        raise_api_error(
            status_code=404,
            error_type="LookupError",
            message=str(exc),
        )


@router.delete("/sources/{source_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_source(source_id: str) -> None:
    try:
        service = SourceService()
        service.delete_source(source_id)
    except LookupError as exc:
        raise_api_error(
            status_code=404,
            error_type="LookupError",
            message=str(exc),
        )
    except ValueError as exc:
        raise_api_error(
            status_code=400,
            error_type="ValueError",
            message=str(exc),
        )
