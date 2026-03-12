import re
from sys import prefix


class LLMOutputError(ValueError):
    """ Поднимается, когда вывод LLM недействителен. """


def sanitize_llm_output(text: str) -> str:
    """
    Базовая очистка вывода LLM.
    """

    text = text.strip()

    # удалить общие префиксы из LLms
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

    # нормализовать пробелы
    text = re.sub(r"\s+", "", text)

    return text


def validate_llm_output(text: str) -> None:
    """
    Убедиться, что выходные данные LLM приемлемы.
    """
    if not text:
        raise LLMOutputError("LLM returned empty text")
    if len(text) < 20:
        raise LLMOutputError("LLM output too short")
    if len(text) > 600:
        raise LLMOutputError("LLM output too long")
