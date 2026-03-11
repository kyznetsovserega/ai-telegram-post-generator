from __future__ import annotations

from dataclasses import dataclass

from openai import APIConnectionError, APIStatusError, APITimeoutError, AsyncOpenAI, RateLimitError

from app.ai.base import TextGenerationClient
from app.ai.errors import (
    AiProviderResponseError,
    AiRateLimitError,
    AiTemporaryUnavailableError
)


@dataclass(frozen=True, slots=True)
class OpenAIClientConfig:
    api_key: str
    model: str


class OpenAITextClient(TextGenerationClient):
    """
    Минимальный async-клиент для генерации постов.
    """

    def __init__(self, config: OpenAIClientConfig) -> None:
        self._config = config
        self._client = AsyncOpenAI(api_key=config.api_key)

    async def generate_text(self, *, instructions: str, user_input: str) -> str:
        try:
            resp = await self._client.responses.create(
                model=self._config.model,
                instructions=instructions,
                input=user_input,
            )

        except RateLimitError as exc:
            raise AiRateLimitError(
                "OpenAI quota/rate limit error. Check billing, project budget, and API limits."
            ) from exc
        except (APITimeoutError, APIConnectionError) as exc:
            raise AiTemporaryUnavailableError("OpenAI is temporarily unavailable") from exc
        except APIStatusError as exc:
            raise AiProviderResponseError(
                f"OpenAI API returned status error: {exc.status_code}"
            ) from exc

        return resp.output_text or ""
