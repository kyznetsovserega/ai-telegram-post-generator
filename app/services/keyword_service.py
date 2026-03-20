from __future__ import annotations

from app.config import FILTER_EXCLUDE_KEYWORDS, FILTER_INCLUDE_KEYWORDS
from app.models import KeywordItem, KeywordType
from app.storage import get_keyword_storage


class KeywordService:
    """ Сервис управления keyword-фильтрами. """

    def __init__(self) -> None:
        self.storage = get_keyword_storage()

    def list_all(self) -> list[KeywordItem]:
        """
        Возвращает все keywords.
        Если storage пустой, синхронизирует его начальными
        значениями из config.py.
        """

        default_items = [
                            KeywordItem(value=value, type=KeywordType.INCLUDE)
                            for value in FILTER_INCLUDE_KEYWORDS
                        ] + [
                            KeywordItem(value=value, type=KeywordType.EXCLUDE)
                            for value in FILTER_EXCLUDE_KEYWORDS
                        ]

        self.storage.save_many(default_items)

        return self.storage.list_all()

    def list_by_type(self, keyword_type: KeywordType) -> list[KeywordItem]:
        return [
            item
            for item in self.list_all()
            if item.type == keyword_type
        ]

    def add_keyword(self, keyword_type: KeywordType, value: str) -> KeywordItem:
        item = KeywordItem(value=value, type=keyword_type)
        self.storage.save_many([item])
        return item

    def delete_keyword(self, keyword_type: KeywordType, value: str) -> None:
        normalized_item = KeywordItem(value=value, type=keyword_type)
        items = self.list_all()

        filtered_items = [
            item
            for item in items
            if not (item.type == normalized_item.type and item.value == normalized_item.value)
        ]

        if len(filtered_items) == len(items):
            raise LookupError(
                f"Keyword not found:type={keyword_type.value},value={normalized_item.value}"
            )

        self.storage.write_all(filtered_items)
