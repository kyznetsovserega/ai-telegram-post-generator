from __future__ import annotations

import os


def _env(name: str, default: str) -> str:
    return os.getenv(name, default)


# Celery Redis
CELERY_BROKER_URL = _env("CELERY_BROKER_URL", "redis://localhost:6379/0")
CELERY_RESULT_BACKEND = _env("CELERY_RESULT_BACKEND", CELERY_BROKER_URL)

# Worker -> FastAPI API call
FASTAPI_BASE_URL = _env("FASTAPI_BASE_URL", "http://127.0.0.1:8000")

# Beat
COLLECT_SITES_DEFAULT = _env("COLLECT_SITES_DEFAULT", "habr")  # "habr,vc,rbc"
