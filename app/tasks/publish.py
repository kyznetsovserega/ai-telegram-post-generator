from __future__ import annotations

from app.celery_app import celery_app
from app.config import PUBLISH_DELAY_SECONDS
from app.core.container import get_container
from app.models import LogItem, LogLevel


@celery_app.task(
    name="app.tasks.publish_single_post_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
)
def publish_single_post_task(self, post_id: str) -> dict:
    """
    Публикует один конкретный пост.
    """
    _ = self  # suppress unused warning

    container = get_container()
    log_service = container.log_service
    publish_service = container.publish_service

    result = publish_service.publish_one_post(post_id)

    log_service.add_log(
        LogItem(
            level=LogLevel.INFO if result.get("published") or result.get("skipped") else LogLevel.ERROR,
            message="Single publish task completed",
            source="tasks.publish_single_post_task",
            context=result,
        )
    )

    return result


@celery_app.task(name="app.tasks.schedule_publish_posts_task")
def schedule_publish_posts_task(previous_result: dict | None = None) -> dict:
    """
    Не публикует сам посты.
    Только планирует отдельные publish-задачи с задержкой.

    Логика:
    - берём все publishable posts
    - ставим их в очередь по одному
    - задержка между ними = PUBLISH_DELAY_SECONDS
    """
    _ = previous_result

    container = get_container()
    log_service = container.log_service
    publish_service = container.publish_service

    publishable_posts = publish_service.list_publishable_posts()

    scheduled_post_ids: list[str] = []

    for index, post in enumerate(publishable_posts):
        countdown = index * PUBLISH_DELAY_SECONDS

        publish_single_post_task.apply_async(
            args=[post.id],
            countdown=countdown,
        )
        scheduled_post_ids.append(post.id)

    result = {
        "publishable": len(publishable_posts),
        "scheduled": len(scheduled_post_ids),
        "delay_seconds": PUBLISH_DELAY_SECONDS,
        "scheduled_post_ids": scheduled_post_ids,
    }

    log_service.add_log(
        LogItem(
            level=LogLevel.INFO,
            message="Publish tasks scheduled",
            source="tasks.schedule_publish_posts_task",
            context=result,
        )
    )

    return result


# Оставляем для обратной совместимости, если где-то ещё используется старое имя
@celery_app.task(name="app.tasks.publish_posts_task")
def publish_posts_task(previous_result: dict | None = None) -> dict:
    """
    Совместимость со старым именем задачи.
    Обёртка над schedule_publish_posts_task.
    """
    return schedule_publish_posts_task(previous_result)
