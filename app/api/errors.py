from __future__ import annotations

from typing import NoReturn

from fastapi import FastAPI, HTTPException, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.ai.errors import (
    AiGenerationError,
    AiProviderResponseError,
    AiRateLimitError,
    AiTemporaryUnavailableError,
)


def raise_api_error(
        *,
        status_code: int,
        error_type: str,
        message: str,
) -> NoReturn:
    """Единая точка формирования ошибок API."""
    raise HTTPException(
        status_code=status_code,
        detail={
            "type": error_type,
            "message": message,
        },
    )


def raise_for_ai_error(exc: Exception) -> NoReturn:
    """
    Приводит ошибки AI-интеграции к единому API-формату с HTTP-статусами.
    """
    if isinstance(exc, RuntimeError):
        raise_api_error(
            status_code=500,
            error_type="RuntimeError",
            message=str(exc),
        )
    if isinstance(exc, LookupError):
        raise_api_error(
            status_code=404,
            error_type="LookupError",
            message=str(exc),
        )
    if isinstance(exc, AiRateLimitError):
        raise_api_error(
            status_code=503,
            error_type="AiRateLimitError",
            message=str(exc),
        )
    if isinstance(exc, AiTemporaryUnavailableError):
        raise_api_error(
            status_code=502,
            error_type="AiTemporaryUnavailableError",
            message=str(exc),
        )
    if isinstance(exc, AiProviderResponseError):
        raise_api_error(
            status_code=502,
            error_type="AiProviderResponseError",
            message=str(exc),
        )
    if isinstance(exc, ValueError):
        raise_api_error(
            status_code=502,
            error_type="ValueError",
            message=str(exc),
        )
    if isinstance(exc, AiGenerationError):
        raise_api_error(
            status_code=502,
            error_type="AiGenerationError",
            message=str(exc),
        )

    raise_api_error(
        status_code=502,
        error_type=type(exc).__name__,
        message=f"LLM integration error: {type(exc).__name__}: {exc}",
    )


def register_exception_handlers(app: FastAPI) -> None:
    """
    Подключает единые обработчики ошибок приложения.
    """

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
            request: Request,
            exc: StarletteHTTPException,
    ) -> JSONResponse:
        _ = request

        # если detail уже приходит в нужном формате, не переформатируем повторно.
        if (
                isinstance(exc.detail, dict)
                and "type" in exc.detail
                and "message" in exc.detail
        ):
            error_payload = exc.detail
        else:
            error_payload = {
                "type": "HTTPException",
                "message": str(exc.detail),
            }

        return JSONResponse(
            status_code=exc.status_code,
            content={"error": error_payload},
        )

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
            request: Request,
            exc: RequestValidationError,
    ) -> JSONResponse:
        _ = request

        # ошибки валидации тоже отдаем в общем контракте.
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "type": "ValidationError",
                    "message": "Invalid request data",
                    "details": exc.errors(),
                }
            },
        )
