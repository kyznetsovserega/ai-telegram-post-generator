from __future__ import annotations

from app.celery_app import celery_app
from app.core.container import get_container
from app.models import LogItem, LogLevel, NewsStatus


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
