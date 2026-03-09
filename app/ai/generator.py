from __future__ import annotations

from dataclasses import dataclass

from app.ai.base import TextGenerationClient

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
    def __init__(self, client: TextGenerationClient) -> None:
        self._client = client

    async def generate_from_text(self, input_text: str) -> GeneratedPost:
        user_input = PROMPT_TEMPLATE.format(input_text=input_text.strip())

        text = await self._client.generate_text(
            instructions=DEFAULT_INSTRUCTIONS,
            user_input=user_input,
        )
        text = text.strip()

        if not text:
            raise ValueError("LLM returned empty text")

        return GeneratedPost(text=text)
