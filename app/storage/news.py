from __future__ import annotations

import hashlib
import json
import logging
from pathlib import Path
from typing import Iterable, Optional

from app.config import (
    REDIS_NEWS_CONTENT_HASH_TTL_SECONDS,
    REDIS_NEWS_ITEM_TTL_SECONDS,
)
from app.models import NewsItem
from app.storage.redis_client import get_redis_client

logger = logging.getLogger(__name__)


def normalize_text(value: str) -> str:
    """
    Нормализует текст для дедупликации.
    """
    return " ".join(value.lower().split())


def generate_content_hash(item: NewsItem) -> str:
    """
    Генерирует content-hash новости.

    Единая функция для:
    - filter service
    - redis storage
    - jsonl storage
    """
    parts = [
        item.title,
        item.summary,
        item.raw_text or "",
    ]
    normalized = normalize_text(" ".join(parts))
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


class JsonlNewsStorage:
    """ Хранилище JSONL для новостей + дедуп по content-hash. """
    HASH_FILE = Path("data/news_hashes.jsonl")

    def __init__(self, path: str | Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.HASH_FILE.parent.mkdir(parents=True, exist_ok=True)

    def _load_hashes(self) -> set[str]:
        if not self.HASH_FILE.exists():
            return set()

        with self.HASH_FILE.open("r", encoding="utf-8") as f:
            return {line.strip() for line in f if line.strip()}

    def _write_all_hashes(self, hashes: Iterable[str]) -> None:
        with self.HASH_FILE.open("w", encoding="utf-8") as file:
            for value in sorted(set(hashes)):
                file.write(value + "\n")

    def _append_hash(self, value: str) -> None:
        with self.HASH_FILE.open("a", encoding="utf-8") as f:
            f.write(value + "\n")

    def save_many(self, items: Iterable[NewsItem]) -> int:
        items_list = list(items)
        if not items_list:
            return 0

        existing_ids = {item.id for item in self.list_all()}
        existing_hashes = self._load_hashes()

        unique_items: list[tuple[NewsItem, str]] = []
        seen_new_ids: set[str] = set()

        for item in items_list:
            if item.id in existing_ids:
                logger.info(
                    "News not saved (duplicate id)",
                    extra={"news_id": item.id},
                )
                continue

            if item.id in seen_new_ids:
                logger.info(
                    "News not saved (duplicate id in batch)",
                    extra={"news_id": item.id},
                )
                continue

            content_hash = item.content_hash or generate_content_hash(item)

            if content_hash in existing_hashes:
                logger.info(
                    "News not saved (duplicate content)",
                    extra={
                        "news_id": item.id,
                        "content_hash": content_hash,
                    },
                )
                continue

            seen_new_ids.add(item.id)
            existing_hashes.add(content_hash)

            unique_items.append(
                (
                    item.model_copy(update={"content_hash": content_hash}),
                    content_hash,
                )
            )

        if not unique_items:
            return 0

        with self.path.open("a", encoding="utf-8") as file:
            for item, content_hash in unique_items:
                file.write(item.model_dump_json() + "\n")
                self._append_hash(content_hash)

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
        Полностью перезаписывает JSONL файл новостей
        и пересобирает индекс content_hash.
        """
        items_list = list(items)

        with self.path.open("w", encoding="utf-8") as file:
            for item in items_list:
                content_hash = item.content_hash or generate_content_hash(item)
                normalized_item = item.model_copy(update={"content_hash": content_hash})
                file.write(normalized_item.model_dump_json() + "\n")

        self._write_all_hashes(
            (item.content_hash or generate_content_hash(item) for item in items_list)
        )



class RedisNewsStorage:
    """Redis-хранилище новостей + дедуп по content-hash (TTL-based)."""

    IDS_KEY = "news:ids"
    HASH_KEY_PREFIX = "news:content_hash:"
    ITEM_KEY_PREFIX = "news:item:"

    def __init__(self) -> None:
        self.redis = get_redis_client()

    @classmethod
    def _item_key(cls, news_id: str) -> str:
        return f"{cls.ITEM_KEY_PREFIX}{news_id}"

    @classmethod
    def _hash_key(cls, content_hash: str) -> str:
        return f"{cls.HASH_KEY_PREFIX}{content_hash}"

    def save_many(self, items: Iterable[NewsItem]) -> int:
        count = 0

        for item in items:
            if self.redis.sismember(self.IDS_KEY, item.id):
                logger.info(
                    "News not saved (duplicate id)",
                    extra={"news_id": item.id},
                )
                continue

            content_hash = item.content_hash or generate_content_hash(item)

            if self.redis.exists(self._hash_key(content_hash)):
                logger.info("News not saved (duplicate content)",
                    extra={
                        "news_id": item.id,
                        "content_hash": content_hash,
                    },
                )
                continue

            normalized_item = item.model_copy(update={"content_hash": content_hash})

            pipeline = self.redis.pipeline()

            pipeline.set(
                self._item_key(normalized_item.id),
                normalized_item.model_dump_json(),
                ex=REDIS_NEWS_ITEM_TTL_SECONDS,
            )
            pipeline.sadd(self.IDS_KEY, normalized_item.id)
            pipeline.set(
                self._hash_key(content_hash),
                "1",
                ex=REDIS_NEWS_CONTENT_HASH_TTL_SECONDS,
            )

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
        """
        Полностью пересобирает Redis-хранилище новостей.
        """
        items_list = list(items)
        existing_ids = self.redis.smembers(self.IDS_KEY)

        pipeline = self.redis.pipeline()

        for news_id in existing_ids:
            pipeline.delete(self._item_key(news_id))

        pipeline.delete(self.IDS_KEY)

        for item in items_list:
            content_hash = item.content_hash or generate_content_hash(item)
            normalized_item = item.model_copy(update={"content_hash": content_hash})

            pipeline.set(
                self._item_key(normalized_item.id),
                normalized_item.model_dump_json(),
                ex=REDIS_NEWS_ITEM_TTL_SECONDS,  # CHANGED
            )
            pipeline.sadd(self.IDS_KEY, normalized_item.id)
            pipeline.set(
                self._hash_key(content_hash),
                "1",
                ex=REDIS_NEWS_CONTENT_HASH_TTL_SECONDS,  # CHANGED
            )

        pipeline.execute()
