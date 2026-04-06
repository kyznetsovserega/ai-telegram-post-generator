from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_log_service
from app.api.errors import get_default_responses
from app.api.schemas import LogListResponse
from app.models import LogLevel
from app.services.log_service import LogService

router = APIRouter()


@router.get(
    "/logs",
    response_model=LogListResponse,
    summary="List logs",
    description="Returns application logs with optional filtering by level and source.",
    responses={
        200: {"description": "Logs returned successfully"},
        **get_default_responses(),
    },
)
async def list_logs(
    level: LogLevel | None = Query(
        default=None,
        description="Filter logs by level",
    ),
    source: str | None = Query(
        default=None,
        description="Filter logs by source",
    ),
    limit: int | None = Query(
        default=None,
        ge=1,
        le=1000,
        description="Maximum number of log records to return",
    ),
    service: LogService = Depends(get_log_service),
) -> LogListResponse:
    logs = service.list_filtered(
        level=level.value if level is not None else None,
        source=source,
        limit=limit,
    )

    items = [
        {
            "id": log.id,
            "created_at": log.created_at,
            "level": log.level,
            "message": log.message,
            "source": log.source,
            "context": log.context,
        }
        for log in logs
    ]

    return LogListResponse(items=items, total=len(items))
