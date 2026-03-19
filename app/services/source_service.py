from __future__ import annotations

from app.models import SourceItem
from app.news_parser.sites import available_source_items
from app.storage import JsonlSourceStorage


class SourceService:
    """ Сервис управления источниками. """

    def __init__(self) -> None:
        self.storage = JsonlSourceStorage()

    def list_all(self) -> list[SourceItem]:
        """
        Возвращает список источников.

        - берем доступные источники (catalog)
        - добавляем отсутствующие в storage
        - возвращаем итоговый список из storage
        """
        catalog_sources = available_source_items()

        self.storage.save_many(catalog_sources)

        return self.storage.list_all()

    def set_enabled(self, source_id: str, enabled: bool) -> SourceItem:
        """ Изменяем состояние источников. """
        sources = self.list_all()

        updated = False
        result: SourceItem | None = None

        for source in sources:
            if source.id == source_id:
                source.enabled = enabled
                updated = True
                result = source
                break
        if not updated or result is None:
            raise LookupError(f"Source not found: {source_id}")

        self.storage.write_all(sources)

        return result
