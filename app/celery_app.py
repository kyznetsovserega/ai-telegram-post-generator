from celery import Celery
from celery.schedules import crontab

from app.config import CELERY_BROKER_URL, CELERY_RESULT_BACKEND

# --- Celery ---
celery_app = Celery(
    "ai_tg_post_generator",
    broker=CELERY_BROKER_URL,
    backend=CELERY_RESULT_BACKEND,
    include=[
        "app.tasks",
    ],
)

# --- Celery Beat ---
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
        }
    },
)
