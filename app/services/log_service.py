from __future__ import annotations

from app.models import LogItem


class LogService:
    """Сервис логирования."""

    def __init__(self, storage):
        self.storage = storage

    def list_all(self) -> list[LogItem]:
        return self.storage.list_all()

    def list_filtered(
            self,
            level: str | None = None,
            source: str | None = None,
            limit: int | None = None,
    ) -> list[LogItem]:
        logs = self.storage.list_all()

        # фильтр по уровню
        if level is not None:
            normalized_level = level.strip().lower()
            logs = [
                log
                for log in logs
                if str(log.level).lower() == normalized_level
                   or getattr(log.level, "value", "").lower() == normalized_level
            ]

        if source is not None:
            normalized_source = source.strip()
            logs = [
                log
                for log in logs
                if log.source == normalized_source
            ]

        logs = sorted(logs, key=lambda item: item.created_at, reverse=True)

        if limit is not None:
            logs = logs[:limit]

        return logs

    def add_log(self, item: LogItem) -> None:
        self.storage.save(item)
