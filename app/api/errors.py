from __future__ import annotations

from typing import NoReturn

from fastapi import HTTPException

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
    # единая точка формирования ошибок API
    raise HTTPException(
        status_code=status_code,
        detail={
            "type": error_type,
            "message": message,
        },
    )


def raise_for_ai_error(exc: Exception) -> NoReturn:
    # AI-ошибки приводим к одному формату,
    # но сохраняем HTTP-статусы по смыслу
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
