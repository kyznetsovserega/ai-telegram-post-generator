from __future__ import annotations

from celery import chain

from app.celery_app import celery_app
from app.core.container import get_container
from app.models import LogItem, LogLevel
from app.tasks.collect import collect_sites_task
from app.tasks.filter import filter_news_task
from app.tasks.generate import generate_posts_task
from app.tasks.publish import schedule_publish_posts_task


@celery_app.task(name="app.tasks.pipeline_chain_task")
def pipeline_chain_task() -> str:
    """
    Orchestration через Celery chain:
    collect -> filter -> generate -> schedule_publish

    - pipeline не публикует посты сразу пачкой
    - последний шаг только планирует отложенные publish-задачи
    - сами публикации идут отдельно, по одной, с countdown
    """
    container = get_container()
    log_service = container.log_service

    workflow = chain(
        collect_sites_task.s(),
        filter_news_task.s(),
        generate_posts_task.s(),
        schedule_publish_posts_task.s(),
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
    Legacy-версия pipeline без chain.
    Оставлена для обратной совместимости и ручной отладки.
    """
    container = get_container()
    log_service = container.log_service

    collect_result = collect_sites_task()
    filter_result = filter_news_task()
    generate_result = generate_posts_task()
    publish_result = schedule_publish_posts_task()

    result = {
        "collect": collect_result,
        "filter": filter_result,
        "generate": generate_result,
        "publish_schedule": publish_result,
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
