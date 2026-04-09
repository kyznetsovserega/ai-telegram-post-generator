from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Protocol

from app.config import REDIS_LOG_ITEM_TTL_SECONDS
from app.models import LogItem
from app.storage.redis_client import get_redis_client


class LogStorageProtocol(Protocol):
    """Контракт хранилища логов."""

    def save(self, item: LogItem) -> None:
        ...

    def save_many(self, items: Iterable[LogItem]) -> int:
        ...

    def list_all(self) -> list[LogItem]:
        ...

    def list_paginated(self, limit: int, offset: int) -> list[LogItem]:
        ...


class JsonlLogStorage:
    """ JSONL-хранилище для логов приложения."""

    def __init__(self, file_path: str | Path = "data/logs.jsonl") -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, item: LogItem) -> None:
        with self.file_path.open("a", encoding="utf-8") as file:
            file.write(item.model_dump_json() + "\n")

    def save_many(self, items: Iterable[LogItem]) -> int:
        items_list = list(items)
        if not items_list:
            return 0

        with self.file_path.open("a", encoding="utf-8") as file:
            for item in items_list:
                file.write(item.model_dump_json() + "\n")

        return len(items_list)

    def list_all(self) -> list[LogItem]:
        if not self.file_path.exists():
            return []

        result: list[LogItem] = []

        with self.file_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue

                payload = json.loads(line)
                result.append(LogItem.model_validate(payload))

        result.sort(key=lambda item: item.created_at, reverse=True)
        return result

    # пагинация для JSONL fallback
    def list_paginated(self, limit: int, offset: int) -> list[LogItem]:
        items = self.list_all()
        return items[offset: offset + limit]

    # count для pagination metadata
    def count_all(self) -> int:
        return len(self.list_all())

class RedisLogStorage:
    """Redis-хранилище для логов приложения."""

    IDS_KEY = "logs:ids"
    ITEM_KEY_PREFIX = "logs:item:"

    def __init__(self) -> None:
        self.redis = get_redis_client()

    @classmethod
    def _item_key(cls, log_id: str) -> str:
        return f"{cls.ITEM_KEY_PREFIX}{log_id}"

    def save(self, item: LogItem) -> None:
        pipeline = self.redis.pipeline()

        pipeline.set(
            self._item_key(item.id),
            item.model_dump_json(),
            ex=REDIS_LOG_ITEM_TTL_SECONDS,
        )
        pipeline.zadd(self.IDS_KEY, {item.id: item.created_at.timestamp()})
        pipeline.execute()

    def save_many(self, items: Iterable[LogItem]) -> int:
        items_list = list(items)
        if not items_list:
            return 0

        pipeline = self.redis.pipeline()

        for item in items_list:
            pipeline.set(
                self._item_key(item.id),
                item.model_dump_json(),
                ex=REDIS_LOG_ITEM_TTL_SECONDS,
            )
            pipeline.zadd(self.IDS_KEY, {item.id: item.created_at.timestamp()})

        pipeline.execute()
        return len(items_list)

    def list_all(self) -> list[LogItem]:
        ids = self.redis.zrevrange(self.IDS_KEY, 0, -1)
        if not ids:
            return []

        pipeline = self.redis.pipeline()
        for log_id in ids:
            pipeline.get(self._item_key(log_id))

        payloads = pipeline.execute()

        result: list[LogItem] = []
        for payload in payloads:
            if not payload:
                continue
            result.append(LogItem.model_validate_json(payload))

        return result

    # пагинация по zset
    def list_paginated(self, limit: int, offset: int) -> list[LogItem]:
        ids = self.redis.zrevrange(self.IDS_KEY, offset, offset + limit - 1)
        if not ids:
            return []

        pipeline = self.redis.pipeline()
        for log_id in ids:
            pipeline.get(self._item_key(log_id))

        payloads = pipeline.execute()

        result: list[LogItem] = []
        for payload in payloads:
            if not payload:
                continue
            result.append(LogItem.model_validate_json(payload))

        return result

    # быстрый count по zset индексу
    def count_all(self) -> int:
        return self.redis.zcard(self.IDS_KEY)
