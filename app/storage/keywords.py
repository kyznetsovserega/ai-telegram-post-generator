from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.models import KeywordItem


class JsonlKeywordStorage:
    """ JSONL-хранилище для keyword-фильтров. """

    def __init__(self, file_path: str | Path = "data/keywords.jsonl") -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def list_all(self) -> list[KeywordItem]:
        """ Возвращает все сохраненные keywords. """
        if not self.file_path.exists():
            return []

        result: list[KeywordItem] = []

        with self.file_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue

                payload = json.loads(line)
                result.append(KeywordItem.model_validate(payload))

        return result

    def save_many(self, items: Iterable[KeywordItem]) -> int:
        """
        Сохраняет только новые keywords по паре (type, value).
        Возвращает количество реально добавленных записей.
        """
        items_list = list(items)

        if not items_list:
            return 0

        existing_keys = {(item.type, item.value) for item in self.list_all()}
        unique_items: list[KeywordItem] = []
        seen_new_keys: set[tuple[str, str]] = set()

        for item in items_list:
            key = (item.type, item.value)

            if key in existing_keys:
                continue

            if key in seen_new_keys:
                continue

            seen_new_keys.add(key)
            unique_items.append(item)

        if not unique_items:
            return 0

        with self.file_path.open("a", encoding="utf-8") as file:
            for item in unique_items:
                file.write(item.model_dump_json() + "\n")

        return len(unique_items)

    def write_all(self, items: Iterable[KeywordItem]) -> None:
        """ Полностью перезаписывает JSONL-файл keywords. """
        items_list = list(items)

        with self.file_path.open("w", encoding="utf-8") as file:
            for item in items_list:
                file.write(item.model_dump_json() + "\n")
