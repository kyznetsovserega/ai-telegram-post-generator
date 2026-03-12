from __future__ import annotations

import asyncio

from dataclasses import dataclass

from app.ai.base import TextGenerationClient
from app.ai.errors import AiTemporaryUnavailableError
from app.ai.validators import sanitize_llm_output, validate_llm_output
from app.models import NewsItem

DEFAULT_INSTRUCTIONS = (
    "Ты редактор новостного Telegram-канала. "
    "Переписывай новости кратко и понятно на русском языке. "
    "Формат: 1 абзац (2–4 коротких предложения). "
    "Передавай только суть новости. "
    "Без воды, без кликбейта. "
    "Не добавляй фактов, которых нет во входном тексте. "
    "Emoji: 0–2 уместных. "
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

        text = sanitize_llm_output(text)
        validate_llm_output(text)

        return GeneratedPost(text=text)

    async def generate_from_news(self, news_item: NewsItem) -> GeneratedPost:
        input_text = self._build_news_input(news_item)
        return await self.generate_from_text(input_text)

    async def _generate_with_retry(self, *, instructions: str, user_input: str) -> str:
        last_error: AiTemporaryUnavailableError | None = None

        for attempt in range(1, self._MAX_ATTEMPTS + 1):
            try:
                return await self._client.generate_text(
                    instructions=instructions,
                    user_input=user_input,
                )
            except AiTemporaryUnavailableError as exc:
                last_error = exc

                if attempt == self._MAX_ATTEMPTS:
                    break

                await asyncio.sleep(self._RETRY_DELAY_SECONDS)

        if last_error is not None:
            raise last_error

        raise RuntimeError("Retry pipeline failed unexpectedly")

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

        if raw_text:
            parts.append(f"Текст: {raw_text}")

        if url:
            parts.append(f"Ссылка: {url}")

        parts.append(f"Дата публикации: {news_item.published_at.isoformat()}")

        has_meaningful_content = any([title, summary, raw_text])

        if not has_meaningful_content:
            raise ValueError("News item does not contain enough text for generation")

        return "\n".join(parts)
