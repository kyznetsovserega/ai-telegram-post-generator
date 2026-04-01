from __future__ import annotations

import re


class LLMOutputError(ValueError):
    """Ошибка валидации ответа LLM."""


def sanitize_llm_output(text: str) -> str:
    """Очистка текста от мусора LLM."""

    text = text.strip()

    prefixes = [
        "here is the telegram post:",
        "telegram post:",
        "post:",
    ]

    lowered = text.lower()

    for p in prefixes:
        if lowered.startswith(p):
            text = text[len(p):].strip()
            break

    text = re.sub(r"\s+", " ", text)

    return text


def validate_llm_output(text: str) -> None:
    """Валидация результата генерации."""

    if not text:
        raise LLMOutputError("LLM returned empty text")
    if len(text) < 20:
        raise LLMOutputError("LLM output too short")
    if len(text) > 600:
        raise LLMOutputError("LLM output too long")
    if " " not in text:
        raise LLMOutputError("LLM output does not contain spaces")

    max_compact_token_length = 40

    tokens = re.findall(r"\S+", text)

    for token in tokens:

        # пропускаем URL
        if token.startswith("http://") or token.startswith("https://"):
            continue

        # пропускаем email
        if "@" in token:
            continue

        # пропускаем emoji и спецсимволы
        cleaned = re.sub(r"[^\wа-яА-ЯёЁ]", "", token)

        if len(cleaned) > max_compact_token_length:
            raise LLMOutputError("LLM output contains malformed compact text")
