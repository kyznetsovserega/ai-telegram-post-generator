from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable, Optional

from app.models import NewsItem
from app.storage.redis_client import get_redis_client


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


class RedisNewsStorage:
    """ Redis-хранилище для новостей. """

    IDS_KEY = "news:ids"
    ITEM_KEY_PREFIX = "news:item:"

    def __init__(self) -> None:
        self.redis = get_redis_client()

    @classmethod
    def _item_key(cls, news_id: str) -> str:
        return f"{cls.ITEM_KEY_PREFIX}{news_id}"

    def save_many(self, items: Iterable[NewsItem]) -> int:
        count = 0

        for item in items:
            if self.redis.sismember(self.IDS_KEY, item.id):
                continue

            pipeline = self.redis.pipeline()
            pipeline.set(self._item_key(item.id), item.model_dump_json())
            pipeline.sadd(self.IDS_KEY, item.id)
            pipeline.execute()

            count += 1

        return count

    def list_all(self) -> list[NewsItem]:
        ids = sorted(self.redis.smembers(self.IDS_KEY))
        if not ids:
            return []

        pipeline = self.redis.pipeline()
        for news_id in ids:
            pipeline.get(self._item_key(news_id))

        payloads = pipeline.execute()

        result: list[NewsItem] = []
        for payload in payloads:
            if not payload:
                continue
            result.append(NewsItem.model_validate_json(payload))

        return result

    def get_by_id(self, news_id: str) -> Optional[NewsItem]:
        payload = self.redis.get(self._item_key(news_id))
        if not payload:
            return None

        return NewsItem.model_validate_json(payload)

    def write_all(self, items: Iterable[NewsItem]) -> None:
        items_list = list(items)

        existing_ids = self.redis.smembers(self.IDS_KEY)

        pipeline = self.redis.pipeline()

        for news_id in existing_ids:
            pipeline.delete(self._item_key(news_id))

        pipeline.delete(self.IDS_KEY)

        for item in items_list:
            pipeline.set(self._item_key(item.id), item.model_dump_json())
            pipeline.sadd(self.IDS_KEY, item.id)

        pipeline.execute()
