from celery import Celery
from celery.schedules import crontab

from app.config import (
    CELERY_BROKER_URL,
    CELERY_RESULT_BACKEND,
    REDIS_CLEANUP_SCHEDULE_HOUR_UTC,
    REDIS_CLEANUP_SCHEDULE_MINUTE_UTC,
)

# Celery
celery_app = Celery(
    "ai_tg_post_generator",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "app.tasks.collect",
        "app.tasks.filter",
        "app.tasks.generate",
        "app.tasks.publish",
        "app.tasks.pipeline",
        "app.tasks.cleanup",
    ],
)

# Celery Beat
celery_app.conf.update(
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="UTC",
    enable_utc=True,
    beat_schedule={
        "collect-sites-every-30-minutes": {
            "task": "app.tasks.pipeline_chain_task",
            "schedule": crontab(minute="*/30"),
        },
        "cleanup-redis-indexes-daily": {
            "task": "app.tasks.cleanup.cleanup_indexes",
            "schedule": crontab(
                hour=REDIS_CLEANUP_SCHEDULE_HOUR_UTC,
                minute=REDIS_CLEANUP_SCHEDULE_MINUTE_UTC,
            ),
        },
    },
)
