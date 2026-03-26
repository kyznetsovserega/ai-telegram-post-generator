from __future__ import annotations

import asyncio

from celery import Celery, chain
from celery.schedules import crontab

from app.config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    COLLECT_SITES_DEFAULT,
)
from app.core.container import get_container
from app.models import LogItem, LogLevel, NewsStatus

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
        "task": "app.tasks.pipeline_chain_task",
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
    container = get_container()
    log_service = container.log_service
    news_service = container.news_service

    requested_sites = [
        site.strip()
        for site in COLLECT_SITES_DEFAULT.split(",")
        if site.strip()]

    processed_sites, collected, saved = asyncio.run(
        news_service.collect_from_sites(
            sites=requested_sites,
            limit_per_site=3,
        )
    )

    result = {
        "requested_sites": requested_sites,
        "processed_sites": processed_sites,
        "collected": collected,
        "saved": saved,
    }

    log_service.add_log(
        LogItem(
            level=LogLevel.INFO,
            message="Collect task completed",
            source="tasks.collect_sites_task",
            context=result,
        )
    )

    return result


@celery_app.task(name="app.tasks.filter_news_task")
def filter_news_task(previous_result: dict | None = None) -> dict:
    """
    Фильтрация только новых новостей с изменением их статуса.
    """
    _ = previous_result

    container = get_container()
    log_service = container.log_service
    news_service = container.news_service
    filter_service = container.filter_service

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

    news_service.update_items(updated_items)

    result = {
        "total": len(new_items),
        "filtered": len(filtered_items),
        "dropped": len(dropped_items),
    }

    log_service.add_log(
        LogItem(
            level=LogLevel.INFO,
            message="Filter task completed",
            source="tasks.filter_news_task",
            context=result,
        )
    )

    return result


@celery_app.task(name="app.tasks.generate_posts_task")
def generate_posts_task(previous_result: dict | None = None) -> dict:
    """
    Генерация постов только для news со статусом FILTERED.
    После успешной генерации news помечается как GENERATED.
    """
    _ = previous_result

    container = get_container()
    log_service = container.log_service
    news_service = container.news_service
    generation_service = container.generation_service
    post_service = container.post_service

    all_items = news_service.list_all()
    filtered_items = [
        item for item in all_items if item.status == NewsStatus.FILTERED
    ]

    generation_result = asyncio.run(
        generation_service.generate_for_news_items(filtered_items)
    )

    # читаем все созданные посты
    posts = post_service.list_all()
    generated_news_ids = {post.news_id for post in posts}

    updated_items: list = []

    for item in all_items:
        if item.status == NewsStatus.FILTERED and item.id in generated_news_ids:
            updated_items.append(
                item.model_copy(update={"status": NewsStatus.GENERATED})
            )
        else:
            updated_items.append(item)

    news_service.replace_all(updated_items)

    log_service.add_log(
        LogItem(
            level=LogLevel.INFO,
            message="Generate task completed",
            source="tasks.generate_posts_task",
            context=generation_result,
        )
    )
    return generation_result


@celery_app.task(name="app.tasks.publish_posts_task")
def publish_posts_task(previous_result: dict | None = None) -> dict:
    """
    Публикация постов, уже сгенерированных AI.
    """
    _ = previous_result

    container = get_container()
    log_service = container.log_service
    publish_service = container.publish_service

    result = publish_service.publish_generated_posts

    log_service.add_log(
        LogItem(
            level=LogLevel.INFO,
            message="Publish task completed",
            source="tasks.publish_posts_task",
            context=result,
        )
    )

    return result


@celery_app.task(name="app.tasks.pipeline_chain_task")
def pipeline_chain_task() -> str:
    """
    Orchestration через Celery chain:
    collect -> filter -> generate -> publish
    """

    container = get_container()
    log_service = container.log_service

    workflow = chain(
        collect_sites_task.s(),
        filter_news_task.s(),
        generate_posts_task.s(),
        publish_posts_task.s(),
    )
    result = workflow.apply_async()

    log_service.add_log(
        LogItem(
            level=LogLevel.INFO,
            message="Pipeline chain started",
            source="tasks.pipeline_chain_task",
            context={"celery_task_id": result.id},
        )
    )
    return result.id


@celery_app.task(name="app.tasks.collect_filter_generate_posts_task")
def collect_filter_generate_posts_task() -> dict:
    """
    Временная legacy-версия pipeline без chain.
    """
    container = get_container()
    log_service = container.log_service

    collect_result = collect_sites_task()
    filter_result = filter_news_task()
    generate_result = generate_posts_task()

    result = {
        "collect": collect_result,
        "filter": filter_result,
        "generate": generate_result,
    }
    log_service.add_log(
        LogItem(
            level=LogLevel.INFO,
            message="Legacy collect-filter-generate pipeline completed",
            source="tasks.collect_filter_generate_posts_task",
            context=result,
        )
    )

    return result
