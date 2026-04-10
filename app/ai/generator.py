from __future__ import annotations

import asyncio
import re
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
    # оставляем 3 попытки только для временных технических сбоев,
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
        last_raw_text: str | None = None

        for attempt in range(1, self._MAX_ATTEMPTS + 1):
            try:
                raw_text = await self._client.generate_text(
                    instructions=instructions,
                    user_input=user_input,
                )
                last_raw_text = raw_text

                text = sanitize_llm_output(raw_text)
                validate_llm_output(text)

                return text

            except AiRateLimitError as exc:
                # при rate limit НЕ делаем новые запросы внутри одного item.
                raise exc

            except AiTemporaryUnavailableError as exc:
                last_temporary_error = exc

            except LLMOutputError as exc:
                last_output_error = exc

                # сначала пытаемся починить текст локально, без нового запроса к LLM.
                if last_raw_text:
                    locally_repaired = self._try_local_repair(last_raw_text)
                    if locally_repaired is not None:
                        return locally_repaired

                # не делаем repair/regenerate через новый LLM-запрос.
                raise exc

            if attempt == self._MAX_ATTEMPTS:
                break

            await asyncio.sleep(self._get_retry_delay(attempt))

        if last_output_error is not None:
            raise last_output_error

        if last_temporary_error is not None:
            raise last_temporary_error

        raise RuntimeError("Retry pipeline failed unexpectedly")

    @classmethod
    def _get_retry_delay(cls, attempt: int) -> float:
        return cls._RETRY_DELAY_SECONDS * (2 ** (attempt - 1))

    @staticmethod
    def _try_local_repair(text: str) -> str | None:
        # локальная починка без обращения к LLM
        repaired = sanitize_llm_output(text)
        repaired = re.sub(r"\s+", " ", repaired).strip()

        if " " not in repaired:
            return None

        try:
            validate_llm_output(repaired)
            return repaired
        except LLMOutputError:
            return None

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
