from __future__ import annotations

from typing import Any, NoReturn

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
from app.api.schemas import ErrorResponse


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
    """Приводит ошибки AI-интеграции к единому API-формату."""
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
            status_code=503,
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
            status_code=400,
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


def _make_json_safe(value: Any) -> Any:
    """Преобразует значение в JSON-safe формат."""
    if isinstance(value, dict):
        return {str(key): _make_json_safe(val) for key, val in value.items()}

    if isinstance(value, list):
        return [_make_json_safe(item) for item in value]

    if isinstance(value, tuple):
        return [_make_json_safe(item) for item in value]

    if isinstance(value, BaseException):
        return str(value)

    return value


def register_exception_handlers(app: FastAPI) -> None:
    """Подключает единые обработчики ошибок приложения."""

    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
            request: Request,
            exc: StarletteHTTPException,
    ) -> JSONResponse:
        _ = request

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

        safe_errors = [_make_json_safe(error) for error in exc.errors()]

        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "type": "ValidationError",
                    "message": "Invalid request data",
                    "details": safe_errors,
                }
            },
        )


def get_default_responses() -> dict[int, dict[str, Any]]:
    """Базовые ответы ошибок для большинства endpoint'ов."""
    return {
        400: {
            "model": ErrorResponse,
            "description": "Bad request",
        },
        422: {
            "model": ErrorResponse,
            "description": "Validation error",
        },
        500: {
            "model": ErrorResponse,
            "description": "Internal server error",
        },
    }


def get_ai_responses() -> dict[int, dict[str, Any]]:
    """Расширенные ответы ошибок для endpoint'ов AI-генерации."""
    responses = get_default_responses()
    responses[502] = {
        "model": ErrorResponse,
        "description": "LLM provider error",
    }
    responses[503] = {
        "model": ErrorResponse,
        "description": "LLM provider temporarily unavailable or rate limited",
    }
    return responses
