from __future__ import annotations


class AiGenerationError(Exception):
    """Базовая ошибка AI generation pipeline."""


class AiRateLimitError(AiGenerationError):
    """Превышен лимит запросов/квоты."""


class AiTemporaryUnavailableError(AiGenerationError):
    """Временная недоступность провайдера или timeout."""


class AiProviderResponseError(AiGenerationError):
    """Некорректный ответ от провайдера."""
