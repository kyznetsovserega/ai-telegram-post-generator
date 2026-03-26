from __future__ import annotations

from fastapi import APIRouter, Query

from app.api.schemas import LogItemResponse, LogListResponse
from app.services.log_service import LogService

router = APIRouter()


@router.get("/logs", response_model=LogListResponse)
async def list_logs(
        level: str | None = Query(default=None),
        source: str | None = Query(default=None),
        limit: int | None = Query(default=None, ge=1, le=1000),
) -> LogListResponse:
    service = LogService()
    logs = service.list_filtered(
        level=level,
        source=source,
        limit=limit,
    )

    items = [
        LogItemResponse(
            id=log.id,
            created_at=log.created_at,
            level=log.level,
            message=log.message,
            source=log.source,
            context=log.context,
        )
        for log in logs
    ]

    return LogListResponse(items=items, total=len(items))
