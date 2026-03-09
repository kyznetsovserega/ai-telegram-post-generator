from __future__ import annotations

from dataclasses import dataclass

from openai import AsyncOpenAI

from app.ai.base import TextGenerationClient


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
        resp = await self._client.responses.create(
            model=self._config.model,
            instructions=instructions,
            input=user_input,
        )

        return resp.output_text or ""
