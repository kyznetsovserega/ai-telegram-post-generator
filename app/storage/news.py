from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from app.models import NewsItem


class JsonlNewsStorage:
    """ Хранилище JSONL для анализируемых новостей. """

    def __init__(self, path: str | Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save_many(self, items: Iterable[NewsItem]) -> int:
        """Сохраняет только новые новости, которых ещё нет по id."""
        items_list = list(items)

        if not items_list:
            return 0

        existing_ids = {item.id for item in self.list_all()}
        unique_items: list[NewsItem] = []
        seen_new_ids: set[str] = set()

        for item in items_list:
            if item.id in existing_ids:
                continue

            if item.id in seen_new_ids:
                continue

            seen_new_ids.add(item.id)
            unique_items.append(item)

        if not unique_items:
            return 0

        with self.path.open("a", encoding="utf-8") as file:
            for item in unique_items:
                file.write(item.model_dump_json() + "\n")

        return len(unique_items)

    def list_all(self) -> list[NewsItem]:
        """ Возврат всех сохраненных новостей. """
        if not self.path.exists():
            return []

        result: list[NewsItem] = []

        with self.path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()

                if not line:
                    continue

                payload = json.loads(line)
                result.append(NewsItem.model_validate(payload))

        return result

    def get_by_id(self, news_id: str) -> Optional[NewsItem]:
        """ Вернуть новость по ее id. """
        for item in self.list_all():
            if item.id == news_id:
                return item

        return None

    def write_all(self, items: Iterable[NewsItem]) -> None:
        """
        Полностью перезаписывает JSONL файл новостей.

        Используется pipeline'ом, чтобы обновить статусы новостей.
        """
        items_list = list(items)

        with self.path.open("w", encoding="utf-8") as file:
            for item in items_list:
                file.write(item.model_dump_json() + "\n")
