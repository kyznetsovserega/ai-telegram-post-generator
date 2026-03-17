from __future__ import annotations

import asyncio

from celery import Celery, chain
from celery.schedules import crontab

from app.config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    COLLECT_SITES_DEFAULT,
)
from app.models import NewsStatus
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
def filter_news_task(previous_result:dict | None=None) -> dict:
    """
    Фильтрация только новых новостей с изменением их статуса.
    """
    news_service = NewsService()
    filter_service = FilterService()

    all_items = news_service.list_all()
    new_items = [item for item in all_items if item.status == NewsStatus.NEW]

    filtered_items, dropped_items = filter_service.apply_filter(new_items)

    filtered_by_id = {item.id: item for item in filtered_items}
    dropped_by_id = {item.id: item for item in dropped_items}

    updated_items = [
        filtered_by_id.get(item.id)
        or dropped_by_id.get(item.id)
        or item
        for item in all_items
    ]

    news_service.replace_all(updated_items)

    return {
        "total": len(new_items),
        "filtered": len(filtered_items),
        "dropped": len(dropped_items),
    }


@celery_app.task(name="app.tasks.generate_posts_task")
def generate_posts_task(previous_result:dict | None=None) -> dict:
    """
    Генерация постов только для news со статусом FILTERED.
    После успешной генерации news помечается как GENERATED.
    """
    news_service = NewsService()
    generation_service = GenerationService()

    all_items = news_service.list_all()
    filtered_items = [
        item for item in all_items if item.status == NewsStatus.FILTERED
    ]

    generation_result = asyncio.run(
        generation_service.generate_for_news_items(filtered_items)
    )

    # читаем все созданные посты
    posts = generation_service.post_storage.list_all()

    generated_news_ids = {
        post.news_id
        for post in posts
    }

    updated_items: list = []

    for item in all_items:

        if (
                item.status == NewsStatus.FILTERED
                and item.id in generated_news_ids
        ):
            updated_items.append(
                item.model_copy(update={"status": NewsStatus.GENERATED})
            )
        else:
            updated_items.append(item)

        news_service.replace_all(updated_items)

    return generation_result


@celery_app.task(name="app.tasks.pipeline_chain_task")
def pipeline_chain_task() -> str:
    """
     Orchestration через Celery chain.
    """
    workflow = chain(
        collect_sites_task.s(),
        filter_news_task.s(),
        generate_posts_task.s(),
    )
    result = workflow.apply_async()

    return result.id

# Временно для сравнения
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
