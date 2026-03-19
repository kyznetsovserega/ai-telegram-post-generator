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
