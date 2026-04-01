from __future__ import annotations

import app.tasks  # noqa: F401
from app.celery_app import celery_app

__all__ = ["celery_app"]
