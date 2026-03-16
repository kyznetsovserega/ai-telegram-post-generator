from __future__ import annotations

import asyncio

from celery import Celery
from celery.schedules import crontab

from app.config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    COLLECT_SITES_DEFAULT,
)
from app.services.filter_service import FilterService
from app.services.generation_service import GenerationService
from app.services.news_service import NewsService

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
        "task": "app.tasks.collect_sites_task",
        "schedule": crontab(minute="*/30"),
        "args": (),
    }
}


@celery_app.task(name="app.tasks.ping")
def ping() -> dict:
    return {"ok": True}


@celery_app.task(name="app.tasks.collect_sites_task")
def collect_sites_task() -> dict:
    """
    Celery task для сбора новостей напрямую через service layer.
    """
    sites = [site.strip() for site in COLLECT_SITES_DEFAULT.split(",") if site.strip()]
    service = NewsService()

    requested_sites, collected, saved = asyncio.run(
        service.collect_from_sites(
            sites=sites,
            limit_per_site=3,
        )
    )

    return {
        "requested_sites": requested_sites,
        "collected": collected,
        "saved": saved,
    }


@celery_app.task(name="app.tasks.filter_news_task")
def filter_news_task() -> dict:
    """
    Минимальная фильтрация новостей.
    """
    news_service = NewsService()
    filter_service = FilterService()

    items = news_service.storage.list_all()
    filtered_items = filter_service.filter_news(items)

    return {
        "total": len(items),
        "filtered": len(filtered_items),
        "dropped": len(items) - len(filtered_items),
    }


@celery_app.task(name="app.tasks.generate_posts_task")
def generate_posts_task() -> dict:
    """
    Генерация постов для новостей после фильтрации.
    """
    news_service = NewsService()
    filter_service = FilterService()
    generation_service = GenerationService()

    items = news_service.storage.list_all()
    filtered_items = filter_service.filter_news(items)

    return asyncio.run(
        generation_service.generate_for_news_items(filtered_items)
    )


@celery_app.task(name="app.tasks.collect_filter_generate_posts_task")
def collect_filter_generate_posts_task() -> dict:
    """
    Полный pipeline:
    collect -> filter -> generate
    """
    collect_result = collect_sites_task()
    filter_result = filter_news_task()
    generate_result = generate_posts_task()

    return {
        "collect": collect_result,
        "filter": filter_result,
        "generate": generate_result,
    }
