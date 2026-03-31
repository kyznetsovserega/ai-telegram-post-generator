from __future__ import annotations

from app.celery_app import celery_app
from app.core.container import get_container
from app.models import LogItem, LogLevel


@celery_app.task(name="app.tasks.publish_posts_task")
def publish_posts_task(previous_result: dict | None = None) -> dict:
    """
    Публикация постов, уже сгенерированных AI.
    """
    _ = previous_result

    container = get_container()
    log_service = container.log_service
    publish_service = container.publish_service

    result = publish_service.publish_generated_posts()

    log_service.add_log(
        LogItem(
            level=LogLevel.INFO,
            message="Publish task completed",
            source="tasks.publish_posts_task",
            context=result,
        )
    )

    return result
