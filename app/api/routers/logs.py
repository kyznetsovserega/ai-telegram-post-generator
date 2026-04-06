from __future__ import annotations

from fastapi import APIRouter, Depends, Query

from app.api.dependencies.services import get_log_service
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
        200: {
            "description": "Logs returned successfully",
            "content": {
                "application/json": {
                    "example": {
                        "items": [
                            {
                                "id": "log_001",
                                "created_at": "2026-04-06T12:00:00Z",
                                "level": "info",
                                "message": "News item dropped by filtering",
                                "source": "tasks.filter_news_task",
                                "context": {
                                    "news_id": "abc123",
                                    "source": "habr",
                                    "status": "dropped",
                                    "reason": "no_include_match",
                                },
                            }
                        ],
                        "total": 1,
                    }
                }
            },
        },
        400: {
            "description": "Invalid query parameters",
        },
        500: {
            "description": "Internal server error",
        },
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
