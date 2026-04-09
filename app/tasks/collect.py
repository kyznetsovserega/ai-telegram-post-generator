from __future__ import annotations

from app.celery_app import celery_app
from app.core.container import get_container
from app.models import LogItem, LogLevel
from app.tasks.task_helpers import get_enabled_source_ids, run_async


@celery_app.task(name="app.tasks.ping")
def ping() -> dict:
    return {"ok": True}


@celery_app.task(
    name="app.tasks.collect_sites_task",
    bind=True,
    autoretry_for=(Exception,),
    retry_backoff=True,
    retry_backoff_max=300,
    retry_jitter=True,
    max_retries=3,
    soft_time_limit=120,
    time_limit=150,
)
def collect_sites_task(self, payload: dict | None = None) -> dict:
    """
    Celery task для сбора новостей через service layer.
    """
    _ = self  # suppress unused warning

    payload = payload or {}

    container = get_container()
    log_service = container.log_service
    news_service = container.news_service

    requested_sites = payload.get("sites")
    if requested_sites is None:
        requested_sites = get_enabled_source_ids()
    else:
        requested_sites = [
            site.strip()
            for site in requested_sites
            if site and site.strip()
        ]

    limit_per_site = int(payload.get("limit_per_site", 3))

    processed_sites, collected, saved = run_async(
        news_service.collect_from_sites(
            sites=requested_sites,
            limit_per_site=limit_per_site,
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
