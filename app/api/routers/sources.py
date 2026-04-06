from __future__ import annotations

from fastapi import APIRouter, Depends, status

from app.api.dependencies.services import get_source_service
from app.api.errors import get_default_responses, raise_api_error
from app.api.schemas import (
    ErrorResponse,
    SourceCreateRequest,
    SourceItemResponse,
    SourceListResponse,
    SourceUpdateRequest,
)
from app.models import SourceType
from app.services.source_service import SourceService

router = APIRouter()


@router.get(
    "/sources",
    response_model=SourceListResponse,
    summary="List sources",
    description="Returns all configured news sources available for collection.",
    responses={
        200: {"description": "Sources returned successfully"},
        **get_default_responses(),
    },
)
async def list_sources(
    service: SourceService = Depends(get_source_service),
) -> SourceListResponse:
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


@router.post(
    "/sources",
    response_model=SourceItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create source",
    description="Creates a custom source for news collection.",
    responses={
        201: {"description": "Source created successfully"},
        **get_default_responses(),
    },
)
async def create_source(
    payload: SourceCreateRequest,
    service: SourceService = Depends(get_source_service),
) -> SourceItemResponse:
    try:
        source = service.create_source(
            source_type=SourceType(payload.type),
            source_id=payload.id,
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
    except ValueError as exc:
        raise_api_error(
            status_code=400,
            error_type="ValueError",
            message=str(exc),
        )


@router.patch(
    "/sources/{source_id}",
    response_model=SourceItemResponse,
    summary="Update source",
    description="Updates source metadata or enabled status.",
    responses={
        200: {"description": "Source updated successfully"},
        404: {
            "description": "Source not found",
            "model": ErrorResponse,
        },
        **get_default_responses(),
    },
)
async def update_source(
    source_id: str,
    payload: SourceUpdateRequest,
    service: SourceService = Depends(get_source_service),
) -> SourceItemResponse:
    try:
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
    except ValueError as exc:
        raise_api_error(
            status_code=400,
            error_type="ValueError",
            message=str(exc),
        )


@router.delete(
    "/sources/{source_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete source",
    description="Deletes a custom source.",
    responses={
        204: {"description": "Source deleted successfully"},
        404: {
            "description": "Source not found",
            "model": ErrorResponse,
        },
        **get_default_responses(),
    },
)
async def delete_source(
    source_id: str,
    service: SourceService = Depends(get_source_service),
) -> None:
    try:
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
