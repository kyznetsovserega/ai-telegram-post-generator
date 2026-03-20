from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.models import KeywordItem
from app.storage.redis_client import get_redis_client


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


class RedisKeywordStorage:
    """ Redis-хранилище для keywords. """

    KEY = "keywords"

    def __init__(self) -> None:
        self.redis = get_redis_client()

    def _make_key(self, item: KeywordItem) -> str:
        return f"{item.type.value}:{item.value}"

    def list_all(self) -> list[KeywordItem]:
        raw_items = self.redis.hgetall(self.KEY)

        result: list[KeywordItem] = []

        for value in raw_items.values():
            payload = json.loads(value)
            result.append(KeywordItem.model_validate(payload))

        return result

    def save_many(self, items: Iterable[KeywordItem]) -> int:
        count = 0

        for item in items:
            key = self._make_key(item)

            if self.redis.hexists(self.KEY, key):
                continue

            self.redis.hset(self.KEY, key, item.model_dump_json())
            count += 1

        return count

    def write_all(self, items: Iterable[KeywordItem]) -> None:
        self.redis.delete(self.KEY)

        for item in items:
            key = self._make_key(item)
            self.redis.hset(self.KEY, key, item.model_dump_json())
