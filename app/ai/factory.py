from __future__ import annotations

from app import config
from app.ai.base import TextGenerationClient
from app.ai.free_llm_client import FreeLLMClientConfig, FreeLLMTextClient
from app.ai.gemini_client import GeminiClientConfig, GeminiTextClient
from app.ai.openai_client import OpenAIClientConfig, OpenAITextClient


def build_text_generation_client(provider: str) -> TextGenerationClient:
    """ Фабрика выбора LLM-провайдера."""

    provider = provider.lower()

    # --- OpenAI ---
    if provider == "openai":
        if not config.OPENAI_API_KEY:
            raise ValueError("OPENAI_API_KEY is not configured")

        return OpenAITextClient(
            OpenAIClientConfig(
                api_key=config.OPENAI_API_KEY,
                model=config.OPENAI_MODEL,
            )
        )

    # --- Gemini ---
    if provider == "gemini":
        if not config.GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")

        return GeminiTextClient(
            GeminiClientConfig(
                api_key=config.GEMINI_API_KEY,
                model=config.GEMINI_MODEL,
            )
        )

    # --- Free LLM ---
    if provider == "free_llm":
        if not config.FREE_LLM_API_KEY:
            raise ValueError("FREE_LLM_API_KEY is not configured")

        return FreeLLMTextClient(
            FreeLLMClientConfig(
                api_key=config.FREE_LLM_API_KEY,
                base_url=config.FREE_LLM_BASE_URL,
                timeout=config.FREE_LLM_TIMEOUT,
            )
        )

    raise ValueError(f"Unsupported LLM_PROVIDER: {provider}")