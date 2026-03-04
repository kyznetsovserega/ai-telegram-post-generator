from __future__ import annotations

from celery import Celery
from celery.schedules import crontab
import requests

from app.config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    COLLECT_SITES_DEFAULT,
    FASTAPI_BASE_URL,
)

celery_app = Celery(
    "ai_tg_post_generator",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
)

celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
)

# Celery Beat: каждые 30 мин запускать сбор новостей
celery_app.conf.beat_schedule = {
    "collect-sites-every-30-minutes": {
        "task": "app.tasks.collect_sites_via_api",
        "schedule": crontab(minute="*/30"),
        "args": (),
    }
}


@celery_app.task(name="app.tasks.ping")
def ping() -> dict:
    return {"ok": True}


@celery_app.task(name="app.tasks.collect_sites_via_api")
def collect_sites_via_api() -> dict:
    """
    Временно : Celery вызывает существующий FastAPI endpoint /api/collect/sites.
    Чтобы быстро получить работающий pipline "beat -> worker -> сбор".
    """
    sites = [s.strip() for s in COLLECT_SITES_DEFAULT.split(",") if s.strip()]
    payload = {"sites": sites, "limit_per_site": 3}

    url = f"{FASTAPI_BASE_URL}/api/collect/sites"
    resp = requests.post(url, json=payload, timeout=30)
    resp.raise_for_status()
    return resp.json()
