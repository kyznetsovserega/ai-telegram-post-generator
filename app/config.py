from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str) -> str:
    """Возвращает строковое значение переменной окружения."""
    return os.getenv(name, default)


def _csv_env(name: str, default: str = "") -> list[str]:
    """Читает CSV-значение из .env и превращает его в список строк."""
    raw_value = os.getenv(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


def _int_env(name: str, default: int) -> int:
    """
    Читает целочисленное значение из .env.
    """
    raw_value = os.getenv(name)
    if raw_value is None or raw_value.strip() == "":
        return default

    try:
        return int(raw_value)
    except ValueError as exc:
        raise ValueError(
            f"Environment variable {name} must be an integer, got: {raw_value!r}"
        ) from exc


# Celery / Redis
CELERY_BROKER_URL = _env("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = _env("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

# App storage backend
STORAGE_BACKEND = _env("STORAGE_BACKEND", "redis").strip().lower()
APP_REDIS_URL = _env("APP_REDIS_URL", CELERY_BROKER_URL)

# Worker -> FastAPI API call
FASTAPI_BASE_URL = _env("FASTAPI_BASE_URL", "http://127.0.0.1:8000")

# Beat
COLLECT_SITES_DEFAULT = _env("COLLECT_SITES_DEFAULT", "habr")  # "habr,vc,rbc"

# Filter rules
FILTER_INCLUDE_KEYWORDS = _csv_env(
    "FILTER_INCLUDE_KEYWORDS",
    "ai, llm, gpt, openai, gemini, python, fastapi, telegram, devops, docker, redis, celery",
)
FILTER_EXCLUDE_KEYWORDS = _csv_env(
    "FILTER_EXCLUDE_KEYWORDS",
    "",
)

# LLM CONFIG
LLM_PROVIDER = _env("LLM_PROVIDER", "openai")

# Open AI
OPENAI_API_KEY = _env("OPENAI_API_KEY", "")
OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-5.2")

# Gemini
GEMINI_API_KEY = _env("GEMINI_API_KEY", "")
GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-2.5-flash")

# APIFREELLM
FREE_LLM_API_KEY = _env("FREE_LLM_API_KEY", "")
FREE_LLM_BASE_URL = _env("FREE_LLM_BASE_URL", "https://apifreellm.com/api/v1/chat")
FREE_LLM_TIMEOUT = _int_env("FREE_LLM_TIMEOUT", 30)

# Telegram publish via Telethon
TELEGRAM_CHANNEL = _env("TELEGRAM_CHANNEL", "")
TELEGRAM_API_ID = _env("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = _env("TELEGRAM_API_HASH", "")

# Единая строковая сессия для publisher и parser
TELEGRAM_SESSION_STRING = _env("TELEGRAM_SESSION_STRING", "").strip()

# Telegram ingest via Telethon
TELEGRAM_SOURCE_CHANNELS = _csv_env(
    "TELEGRAM_SOURCE_CHANNELS",
    "thehackernews,itsfoss_official",
)

# Redis retention policy
REDIS_NEWS_ITEM_TTL_SECONDS = _int_env(
    "REDIS_NEWS_ITEM_TTL_SECONDS",
    7 * 24 * 60 * 60,  # 7 days
)

REDIS_NEWS_CONTENT_HASH_TTL_SECONDS = _int_env(
    "REDIS_NEWS_CONTENT_HASH_TTL_SECONDS",
    14 * 24 * 60 * 60,  # 14 days
)

REDIS_POST_ITEM_TTL_SECONDS = _int_env(
    "REDIS_POST_ITEM_TTL_SECONDS",
    90 * 24 * 60 * 60,  # 90 days
)

REDIS_LOG_ITEM_TTL_SECONDS = _int_env(
    "REDIS_LOG_ITEM_TTL_SECONDS",
    14 * 24 * 60 * 60,  # 14 days
)

# Redis cleanup schedule (UTC)
REDIS_CLEANUP_SCHEDULE_HOUR_UTC = _int_env(
    "REDIS_CLEANUP_SCHEDULE_HOUR_UTC",
    3,
)

REDIS_CLEANUP_SCHEDULE_MINUTE_UTC = _int_env(
    "REDIS_CLEANUP_SCHEDULE_MINUTE_UTC",
    0,
)
