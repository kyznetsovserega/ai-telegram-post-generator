from app.celery_app import celery_app
import app.tasks # noqa: F401

__all__ = ["celery_app"]