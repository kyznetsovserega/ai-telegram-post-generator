from __future__ import annotations

from dataclasses import dataclass

from google import genai

from app.ai.base import TextGenerationClient
from app.ai.errors import AiProviderResponseError, AiTemporaryUnavailableError


@dataclass(frozen=True, slots=True)
class GeminiClientConfig:
    api_key: str
    model: str


class GeminiTextClient(TextGenerationClient):
    def __init__(self, config: GeminiClientConfig) -> None:
        self._config = config
        self._client = genai.Client(api_key=config.api_key)

    async def generate_text(self, *, instructions: str, user_input: str) -> str:
        prompt = (
            f"{instructions}\n\n"
            f"Входящие данные: \n{user_input}"
        )
        try:
            response = await self._client.aio.models.generate_content(
                model=self._config.model,
                contents=prompt,
            )
        except TimeoutError as exc:
            raise AiTemporaryUnavailableError("Gemini is temporarily unavailable") from exc
        except Exception as exc:
            raise AiProviderResponseError(
                f"Gemini integration error: {type(exc).__name__}: {exc}"
            ) from exc

        return (response.text or "").strip()
