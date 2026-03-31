from __future__ import annotations

from app.celery_app import celery_app
from app.core.container import get_container
from app.models import LogItem, LogLevel, NewsStatus
from app.tasks.task_helpers import run_async


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

    generation_result = run_async(
        generation_service.generate_for_news_items(filtered_items)
    )

    # читаем все созданные посты и переводим связанные новости в GENERATED
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

    news_service.update_items(updated_items)

    log_service.add_log(
        LogItem(
            level=LogLevel.INFO,
            message="Generate task completed",
            source="tasks.generate_posts_task",
            context=generation_result,
        )
    )
    return generation_result
