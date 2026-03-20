from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from app.models import SourceItem
from app.storage.redis_client import get_redis_client


class JsonlSourceStorage:
    """ JSONL-хранилище для состояния источников новостей. """

    def __init__(self, file_path: str | Path = "data/sources.jsonl") -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def list_all(self) -> list[SourceItem]:
        """ Возвращает все сохраненные источники. """
        if not self.file_path.exists():
            return []

        result: list[SourceItem] = []

        with self.file_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue

                payload = json.loads(line)
                result.append(SourceItem.model_validate(payload))

        return result

    def get_by_id(self, source_id: str) -> Optional[SourceItem]:
        """ Возвращает источник по его id. """
        for item in self.list_all():
            if item.id == source_id:
                return item
        return None

    def save_many(self, items: Iterable[SourceItem]) -> int:
        """
        Сохраняет только новые источники, которых ещё нет по id.
        Возвращает количество реально добавленных записей.
        """
        items_list = list(items)

        if not items_list:
            return 0

        existing_ids = {item.id for item in self.list_all()}
        unique_items: list[SourceItem] = []
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

        with self.file_path.open("a", encoding="utf-8") as file:
            for item in unique_items:
                file.write(item.model_dump_json() + "\n")

            return len(unique_items)

    def write_all(self, items: Iterable[SourceItem]) -> None:
        """ Полностью перезаписывает JSONL-файл источниковю """
        items_list = list(items)

        with self.file_path.open("w", encoding="utf-8") as file:
            for item in items_list:
                file.write(item.model_dump_json() + "\n")


class RedisSourceStorage:
    """ Redis-хранилище для источников. """

    KEY = "sources"

    def __init__(self) -> None:
        self.redis = get_redis_client()

    def list_all(self) -> list[SourceItem]:
        raw_items = self.redis.hgetall(self.KEY)

        result: list[SourceItem] = []

        for value in raw_items.values():
            payload = json.loads(value)
            result.append(SourceItem.model_validate(payload))

        return result

    def get_by_id(self, source_id: str) -> Optional[SourceItem]:
        raw = self.redis.hget(self.KEY, source_id)

        if not raw:
            return None

        payload = json.loads(raw)
        return SourceItem.model_validate(payload)

    def save_many(self, items: Iterable[SourceItem]) -> int:
        count = 0

        for item in items:
            if self.redis.hexists(self.KEY, item.id):
                continue

            self.redis.hset(self.KEY, item.id, item.model_dump_json())
            count += 1

        return count

    def write_all(self, items: Iterable[SourceItem]) -> None:
        self.redis.delete(self.KEY)

        for item in items:
            self.redis.hset(self.KEY, item.id, item.model_dump_json())
