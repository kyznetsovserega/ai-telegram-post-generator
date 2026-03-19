from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


def _csv_env(name: str, default: str = "") -> list[str]:
    raw_value = os.getenv(name, default)
    return [item.strip() for item in raw_value.split(",") if item.strip()]


# Celery Redis
CELERY_BROKER_URL = _env("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = _env("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

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

# Telegram publish via Telethon
TELEGRAM_CHANNEL = _env("TELEGRAM_CHANNEL", "")
TELEGRAM_API_ID = _env("TELEGRAM_API_ID", "")
TELEGRAM_API_HASH = _env("TELEGRAM_API_HASH", "")
TELEGRAM_SESSION_NAME = _env("TELEGRAM_SESSION_NAME", "telegram_publisher")
