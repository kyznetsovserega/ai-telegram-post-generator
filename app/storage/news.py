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

    # SHA256
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


class JsonlNewsStorage:
    """ Хранилище JSONL для новостей + дедуп по content-hash. """
    HASH_FILE = Path("data/news_hashes.jsonl")

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
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

        # новые сверху
        result.sort(key=lambda item: item.published_at, reverse=True)
        return result

    # добавлена пагинация для JSONL fallback
    def list_paginated(self, limit: int, offset: int) -> list[NewsItem]:
        items = self.list_all()
        return items[offset: offset + limit]

    def get_by_id(self, news_id: str) -> Optional[NewsItem]:
        """ Вернуть новость по ее id. """
        for item in self.list_all():
            if item.id == news_id:
                return item
        return None

    def get_news_id_by_content_hash(self, content_hash: str) -> str | None:
        for item in self.list_all():
            if item.content_hash == content_hash:
                return item.id
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

    # единый интерфейс для service-level dedup
    def exists_content_hash(
            self,
            content_hash: str,
            exclude_news_id: str | None = None,
    ) -> bool:
        if not content_hash:
            return False

        for item in self.list_all():
            if item.content_hash != content_hash:
                continue

            if exclude_news_id is not None and item.id == exclude_news_id:
                continue

            return True

        return False

    # count для pagination metadata
    def count_all(self) -> int:
        return len(self.list_all())

class RedisNewsStorage:
    """Redis-хранилище новостей + дедуп по content-hash (TTL-based)."""

    IDS_KEY = "news:ids"
    HASH_KEY_PREFIX = "news:content_hash:"
    ITEM_KEY_PREFIX = "news:item:"
    # индекс времени публикации для pagination
    PUBLISHED_INDEX_KEY = "news:published_at"

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
                logger.info(
                    "News not saved (duplicate content)",
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

            # hash-ключе храним news_id
            pipeline.set(
                self._hash_key(content_hash),
                normalized_item.id,
                ex=REDIS_NEWS_CONTENT_HASH_TTL_SECONDS,
            )

            # индекс для pagination / сортировки
            pipeline.zadd(
                self.PUBLISHED_INDEX_KEY,
                {normalized_item.id: normalized_item.published_at.timestamp()},
            )

            pipeline.execute()
            count += 1

        return count

    def list_all(self) -> list[NewsItem]:
        # читаем через zset индекс, новые сверху
        ids = self.redis.zrevrange(self.PUBLISHED_INDEX_KEY, 0, -1)
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

    # добавлена пагинация
    def list_paginated(self, limit: int, offset: int) -> list[NewsItem]:
        ids = self.redis.zrevrange(
            self.PUBLISHED_INDEX_KEY,
            offset,
            offset + limit - 1,
        )
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

    def get_news_id_by_content_hash(self, content_hash: str) -> str | None:
        if not content_hash:
            return None
        return self.redis.get(self._hash_key(content_hash))

    def write_all(self, items: Iterable[NewsItem]) -> None:
        """
        Полностью пересобирает Redis-хранилище новостей.
        """
        items_list = list(items)
        existing_ids = self.redis.smembers(self.IDS_KEY)

        pipeline = self.redis.pipeline()

        # удаляем старые item-ключи, hash-индексы и zset-индекс
        for news_id in existing_ids:
            payload = self.redis.get(self._item_key(news_id))
            if payload:
                existing_item = NewsItem.model_validate_json(payload)
                if existing_item.content_hash:
                    pipeline.delete(self._hash_key(existing_item.content_hash))

            pipeline.delete(self._item_key(news_id))

        pipeline.delete(self.IDS_KEY)
        pipeline.delete(self.PUBLISHED_INDEX_KEY)

        for item in items_list:
            content_hash = item.content_hash or generate_content_hash(item)
            normalized_item = item.model_copy(update={"content_hash": content_hash})

            pipeline.set(
                self._item_key(normalized_item.id),
                normalized_item.model_dump_json(),
                ex=REDIS_NEWS_ITEM_TTL_SECONDS,
            )
            pipeline.sadd(self.IDS_KEY, normalized_item.id)

            # храним news_id в hash-индексе
            pipeline.set(
                self._hash_key(content_hash),
                normalized_item.id,
                ex=REDIS_NEWS_CONTENT_HASH_TTL_SECONDS,
            )

            # восстанавливаем zset индекс публикации
            pipeline.zadd(
                self.PUBLISHED_INDEX_KEY,
                {normalized_item.id: normalized_item.published_at.timestamp()},
            )

        pipeline.execute()

    # единый интерфейс для service-level dedup
    def exists_content_hash(
            self,
            content_hash: str,
            exclude_news_id: str | None = None,
    ) -> bool:
        if not content_hash:
            return False

        news_id = self.redis.get(self._hash_key(content_hash))
        if not news_id:
            return False

        if exclude_news_id is not None and news_id == exclude_news_id:
            return False

        return self.redis.exists(self._item_key(news_id)) == 1

    # быстрый count по индексу ids
    def count_all(self) -> int:
        return self.redis.scard(self.IDS_KEY)
