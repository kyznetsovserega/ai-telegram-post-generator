from __future__ import annotations

from app.models import SourceItem, SourceType
from app.news_parser.sites import available_source_items
from app.storage import get_source_storage


class SourceService:
    """ Сервис управления источниками. """

    def __init__(self) -> None:
        self.storage = get_source_storage()

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

    def create_source(self, item: SourceItem) -> SourceItem:
        """
        Добавляет новый источник.

        Ограничение MVP:
        - через API разрешаем создавать только Telegram-источники
        - встроенные site-источники продолжают приходить из catalog
        """
        if item.type != SourceType.TG:
            raise ValueError("Only Telegram sources can be created via API right now")

        if not item.id.startswith("tg:"):
            raise ValueError("Telegram source id must start with 'tg:'")

        existing = self.storage.get_by_id(item.id)
        if existing:
            raise ValueError(f"Source already exists: {item.id}")

        self.storage.save_many([item])

        return item

    def delete_source(self, source_id: str) -> None:
        """
        Удаляет пользовательский источник.

        Важно:
        - встроенные catalog sources удалять нельзя
        """
        catalog_ids = {item.id for item in available_source_items()}

        if source_id in catalog_ids:
            raise ValueError(f"Built-in catalog source cannot be deleted: {source_id}")

        sources = self.storage.list_all()
        filtered_sources = [source for source in sources if source.id != source_id]

        if len(filtered_sources) == len(sources):
            raise LookupError(f"Source not found: {source_id}")

        self.storage.write_all(filtered_sources)
