from __future__ import annotations


class AiGenerationError(Exception):
    """Базовая ошибка AI generation pipeline."""


class AiRateLimitError(AiGenerationError):
    """Провайдер отклонил запрос из-за лимитов или квоты."""


class AiTemporaryUnavailableError(AiGenerationError):
    """Временная ошибка сети, timeout или недоступность провайдера."""


class AiProviderResponseError(AiGenerationError):
    """Провайдер вернул некорректный или неожиданный ответ."""