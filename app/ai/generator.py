from __future__ import annotations

import asyncio

from dataclasses import dataclass

from app.ai.base import TextGenerationClient
from app.ai.errors import AiTemporaryUnavailableError, AiRateLimitError
from app.ai.validators import (
    sanitize_llm_output,
    validate_llm_output,
    LLMOutputError,
)
from app.models import NewsItem

DEFAULT_INSTRUCTIONS = (
    "Ты редактор новостного Telegram-канала."
    "Переписывай новости кратко и понятно на русском языке."
    "Формат: 1 абзац (2–4 коротких предложения)."
    "Передавай только суть новости."
    "Без воды, без кликбейта."
    "Не добавляй фактов, которых нет во входном тексте."
    "Emoji: 0–2 уместных."
    "Если есть ссылка — поставь её в конце."
)

PROMPT_TEMPLATE = """\
Сделай короткий пост для Telegram по новости.

Правила:
- 2–4 коротких предложения в одном абзаце
- 0–2 emoji
- без воды, без кликбейта
- не добавляй фактов, которых нет во входе
- если есть ссылка/URL — добавь в конце

Текст:
{input_text}
"""

REPAIR_INSTRUCTIONS = (
    "Ты редактор новостного Telegram-канала."
    "Исправь текст так, чтобы он был читаемым и естественным на русском языке."
    "Слова должны быть разделены пробелами."
    "Формат: 1 абзац из 2–4 коротких предложений."
    "Не добавляй новых фактов."
)


@dataclass(frozen=True, slots=True)
class GeneratedPost:
    text: str


class PostGenerator:
    _MAX_ATTEMPTS = 3
    _RETRY_DELAY_SECONDS = 1.0

    def __init__(self, client: TextGenerationClient) -> None:
        self._client = client

    async def generate_from_text(self, input_text: str) -> GeneratedPost:
        user_input = PROMPT_TEMPLATE.format(input_text=input_text.strip())

        text = await self._generate_with_retry(
            instructions=DEFAULT_INSTRUCTIONS,
            user_input=user_input,
        )
        return GeneratedPost(text=text)

    async def generate_from_news(self, news_item: NewsItem) -> GeneratedPost:
        input_text = self._build_news_input(news_item)
        return await self.generate_from_text(input_text)

    async def _generate_with_retry(self, *, instructions: str, user_input: str) -> str:
        last_temporary_error: Exception | None = None
        last_output_error: LLMOutputError | None = None

        original_instructions = instructions
        original_user_input = user_input

        current_instructions = instructions
        current_user_input = user_input

        last_raw_text: str | None = None

        for attempt in range(1, self._MAX_ATTEMPTS + 1):
            try:
                raw_text = await self._client.generate_text(
                    instructions=current_instructions,
                    user_input=current_user_input,
                )
                last_raw_text = raw_text

                text = sanitize_llm_output(raw_text)
                validate_llm_output(text)

                return text


            except (AiTemporaryUnavailableError, AiRateLimitError) as exc:
                last_temporary_error = exc

            except LLMOutputError as exc:
                last_output_error = exc
                if attempt < self._MAX_ATTEMPTS:
                    strategy = self._choose_recovery_strategy(exc)

                    if strategy == "regenerate":
                        current_instructions = original_instructions
                        current_user_input = original_user_input

                    elif strategy == "repair" and last_raw_text:
                        repaired_input = self._build_repair_prompt(last_raw_text)

                        current_instructions = REPAIR_INSTRUCTIONS
                        current_user_input = repaired_input

            if attempt == self._MAX_ATTEMPTS:
                break

            await asyncio.sleep(self._RETRY_DELAY_SECONDS * attempt)

        if last_output_error is not None:
            raise last_output_error

        if last_temporary_error is not None:
            raise last_temporary_error

        raise RuntimeError("Retry pipeline failed unexpectedly")

    @staticmethod
    def _choose_recovery_strategy(error: LLMOutputError) -> str:
        message = str(error).lower()

        if "empty" in message:
            return "regenerate"

        if "too short" in message:
            return "regenerate"

        if "too long" in message:
            return "repair"

        if "does not contain spaces" in message:
            return "repair"

        if "malformed compact text" in message:
            return "repair"

        return "regenerate"

    @staticmethod
    def _build_repair_prompt(text: str) -> str:
        cleaned = sanitize_llm_output(text)

        return f"""
Исправь текст ниже.

Требования:
- раздели склеенные слова
- сделай читаемый русский текст
- 2–4 коротких предложения
- один абзац
- не добавляй новых фактов

Текст:
{cleaned}
"""

    @staticmethod
    def _normalize_input_news(input_text: str) -> str:
        normalized = input_text.strip()

        if not normalized:
            raise ValueError("Input text must not be empty")

        return normalized

    @staticmethod
    def _build_news_input(news_item: NewsItem) -> str:
        parts: list[str] = []

        title = news_item.title.strip()
        source = news_item.source.strip()
        summary = (news_item.summary or "").strip()
        raw_text = (news_item.raw_text or "").strip()
        url = (news_item.url or "").strip()

        if title:
            parts.append(f"Заголовок: {title}")

        if source:
            parts.append(f"Источник: {source}")

        if summary:
            parts.append(f"Краткое описание: {summary}")

        if raw_text and not summary:
            parts.append(f"Текст: {raw_text}")

        if url:
            parts.append(f"Ссылка: {url}")

        parts.append(f"Дата публикации: {news_item.published_at.isoformat()}")

        has_meaningful_content = any([title, summary, raw_text])

        if not has_meaningful_content:
            raise ValueError("News item does not contain enough text for generation")

        return "\n".join(parts)
