from __future__ import annotations

from dataclasses import dataclass

import httpx

from app.ai.base import TextGenerationClient
from app.ai.errors import (
    AiProviderResponseError,
    AiRateLimitError,
    AiTemporaryUnavailableError,
)


@dataclass(frozen=True, slots=True)
class FreeLLMClientConfig:
    api_key: str
    base_url: str
    timeout: int = 30


class FreeLLMTextClient(TextGenerationClient):
    """
    Клиент для apifreellm.com
    Sync API -> оборачиваем в async через httpx.AsyncClient
    """

    def __init__(self, config: FreeLLMClientConfig) -> None:
        self._config = config

    async def generate_text(self, *, instructions: str, user_input: str) -> str:
        prompt = f"{instructions}\n\n{user_input}"

        payload = {
            "message": prompt
        }

        try:
            async with httpx.AsyncClient(timeout=self._config.timeout) as client:
                response = await client.post(
                    self._config.base_url,
                    json=payload,
                    headers={
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self._config.api_key}",
                    },
                )

            if response.status_code == 429:
                raise AiRateLimitError("Free LLM rate limit")

            if response.status_code >= 500:
                raise AiTemporaryUnavailableError(
                    f"Free LLM temporary error: {response.status_code}"
                )

            if response.status_code != 200:
                raise AiProviderResponseError(
                    f"Free LLM bad response: {response.status_code} {response.text}"
                )

            data = response.json()

            text = data.get("response") or data.get("text") or ""

            return text.strip()

        except httpx.TimeoutException as exc:
            raise AiTemporaryUnavailableError("Free LLM timeout") from exc

        except httpx.RequestError as exc:
            raise AiTemporaryUnavailableError(
                f"Free LLM connection error: {exc}"
            ) from exc
