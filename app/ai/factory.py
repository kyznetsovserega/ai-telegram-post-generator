from __future__ import annotations

from app import config
from app.ai.base import TextGenerationClient
from app.ai.gemini_client import GeminiClientConfig, GeminiTextClient
from app.ai.openai_client import OpenAIClientConfig, OpenAITextClient


def build_text_generation_client() -> TextGenerationClient:
    """Фабрика выбора LLM-провайдера."""

    provider = config.LLM_PROVIDER.lower()

    if provider == "openai":
        return OpenAITextClient(
            OpenAIClientConfig(
                api_key=config.OPENAI_API_KEY,
                model=config.OPENAI_MODEL,
            )
        )

    if provider == "gemini":
        return GeminiTextClient(
            GeminiClientConfig(
                api_key=config.GEMINI_API_KEY,
                model= config.GEMINI_MODEL,
            )
        )
    raise ValueError(f"Unsupported LLM_PROVIDER:{config.LLM_PROVIDER}")
