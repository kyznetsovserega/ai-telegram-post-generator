from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


# Celery Redis
CELERY_BROKER_URL = _env("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = _env("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

# Worker -> FastAPI API call
FASTAPI_BASE_URL = _env("FASTAPI_BASE_URL", "http://127.0.0.1:8000")

# Beat
COLLECT_SITES_DEFAULT = _env("COLLECT_SITES_DEFAULT", "habr")  # "habr,vc,rbc"

# LLM CONFIG
LLM_PROVIDER = _env("LLM_PROVIDER", "openai")

# Open AI
OPENAI_API_KEY = _env("OPENAI_API_KEY","")
OPENAI_MODEL = _env("OPENAI_MODEL", "gpt-5.2")

# Gemini
GEMINI_API_KEY = _env("GEMINI_API_KEY", "")
GEMINI_MODEL = _env("GEMINI_MODEL", "gemini-2.5-flash")

