from __future__ import annotations

from app.models import LogItem


class LogService:
    """Сервис логирования."""

    def __init__(self, storage):
        self.storage = storage

    def list_all(self) -> list[LogItem]:
        return self.storage.list_all()

    # count_all для пагинации API
    def count_all(self) -> int:
        if hasattr(self.storage, "count_all"):
            return self.storage.count_all()

        return len(self.storage.list_all())

    # paginated list без фильтров
    def list_paginated(
            self,
            limit: int,
            offset: int,
    ) -> list[LogItem]:
        if hasattr(self.storage, "list_paginated"):
            return self.storage.list_paginated(limit=limit, offset=offset)

        logs = self.storage.list_all()
        return logs[offset: offset + limit]

    def list_filtered(
            self,
            level: str | None = None,
            source: str | None = None,
            limit: int | None = None,
            offset: int = 0,
    ) -> tuple[list[LogItem], int]:
        """
        Метод возвращает:
        - список логов для текущей страницы
        - total после применения фильтров, но до пагинации
        """

        no_filters = level is None and source is None

        if no_filters:
            if limit is None:
                logs = self.list_all()
                return logs, len(logs)

            logs = self.list_paginated(limit=limit, offset=offset)
            return logs, self.count_all()

        logs = self.storage.list_all()

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

        # total по фильтрам до slice
        total = len(logs)

        if limit is not None:
            logs = logs[offset: offset + limit]
        elif offset:
            logs = logs[offset:]

        return logs, total

    def add_log(self, item: LogItem) -> None:
        self.storage.save(item)
