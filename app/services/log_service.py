from __future__ import annotations

from app.models import LogItem
from app.storage import get_log_storage


class LogService:
    """Сервис работы с логами."""

    def __init__(self) -> None:
        self.storage = get_log_storage()

    def list_all(self) -> list[LogItem]:
        return self.storage.list_all()

    def add_log(self, item: LogItem) -> None:
        self.storage.save(item)
