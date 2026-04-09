from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Optional, Iterable

from app.config import REDIS_POST_ITEM_TTL_SECONDS
from app.models import PostItem, PostStatus
from app.storage.redis_client import get_redis_client


# единая нормализация текста для индекса generated_text
def normalize_generated_text(text: str) -> str:
    return " ".join(text.strip().split())


# отдельный hash для Redis-ключа индекса generated_text
def generate_generated_text_hash(text: str) -> str:
    normalized = normalize_generated_text(text)
    return hashlib.md5(normalized.encode("utf-8")).hexdigest()


class JsonlPostStorage:
    """ JSONL-хранилище для сгенерированных сообщений Telegram. """

    def __init__(self, file_path: str | Path = "data/posts.jsonl") -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, post: PostItem) -> None:
        """
        Добавление нового поста в файл JSONL.
        Метод используется как append для новых постов.
        """
        with self.file_path.open("a", encoding="utf-8") as file:
            file.write(post.model_dump_json() + "\n")

    def list_all(self) -> list[PostItem]:
        """Возвращает все сохранённые посты."""
        if not self.file_path.exists():
            return []

        result: list[PostItem] = []

        with self.file_path.open("r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if not line:
                    continue

                payload = json.loads(line)
                result.append(PostItem.model_validate(payload))

        # новые сверху
        result.sort(key=lambda item: item.created_at, reverse=True)
        return result

    # добавлена пагинация для JSONL fallback
    def list_paginated(self, limit: int, offset: int) -> list[PostItem]:
        items = self.list_all()
        return items[offset: offset + limit]

    def get_by_id(self, post_id: str) -> Optional[PostItem]:
        """Возвращает пост по его id."""
        for item in self.list_all():
            if item.id == post_id:
                return item
        return None

    def get_by_news_id(self, news_id: str) -> Optional[PostItem]:
        """ Возвращает первое сообщение, созданное из данной новости. """
        for item in self.list_all():
            if item.news_id == news_id:
                return item
        return None

    def get_by_generated_text(self, text: str) -> Optional[PostItem]:
        """ Вернуть сообщение с идентичным сгенерированным текстом. """
        normalized = normalize_generated_text(text)  # CHANGED

        for item in self.list_all():
            if normalize_generated_text(item.generated_text) == normalized:  # CHANGED
                return item
        return None

    def list_publishable(self) -> list[PostItem]:
        """ Возвращает только посты, готовые к публикации."""
        return [
            item for item in self.list_all()
            if (
                    item.status == PostStatus.GENERATED
                    and item.published_at is None
                    and item.external_message_id is None
            )
        ]

    def update(self, post: PostItem) -> None:
        """ Обновляет существующий пост по id. """
        items = self.list_all()

        updated = False
        result: list[PostItem] = []

        for item in items:
            if item.id == post.id:
                result.append(post)
                updated = True
            else:
                result.append(item)

        if not updated:
            raise LookupError(f"Post not found: {post.id}")

        self.write_all(result)

    def write_all(self, items: Iterable[PostItem]) -> None:
        """
        Полностью перезаписывает JSONL-файл постов.
        """
        items_list = list(items)

        with self.file_path.open("w", encoding="utf-8") as file:
            for item in items_list:
                file.write(item.model_dump_json() + "\n")

    # count для pagination metadata
    def count_all(self) -> int:
        return len(self.list_all())


class RedisPostStorage:
    """Redis-хранилище для сгенерированных сообщений Telegram."""

    IDS_KEY = "posts:ids"
    ITEM_KEY_PREFIX = "posts:item:"
    # индекс для быстрого поиска поста по news_id
    NEWS_INDEX_PREFIX = "posts:by_news_id:"
    # индекс для пагинации и сортировки по времени создания
    CREATED_INDEX_KEY = "posts:created_at"
    # индекс для быстрого поиска поста по generated_text
    GENERATED_TEXT_INDEX_PREFIX = "posts:by_generated_text:"

    def __init__(self) -> None:
        self.redis = get_redis_client()

    @classmethod
    def _item_key(cls, post_id: str) -> str:
        return f"{cls.ITEM_KEY_PREFIX}{post_id}"

    # helper для news_id -> post_id
    @classmethod
    def _news_index_key(cls, news_id: str) -> str:
        return f"{cls.NEWS_INDEX_PREFIX}{news_id}"

    # helper для generated_text_hash -> post_id
    @classmethod
    def _generated_text_index_key(cls, text_hash: str) -> str:
        return f"{cls.GENERATED_TEXT_INDEX_PREFIX}{text_hash}"

    def save(self, post: PostItem) -> None:
        pipeline = self.redis.pipeline()

        existing = self.get_by_id(post.id)
        if existing is not None:
            old_text_hash = generate_generated_text_hash(existing.generated_text)
            new_text_hash = generate_generated_text_hash(post.generated_text)
            if old_text_hash != new_text_hash:
                pipeline.delete(self._generated_text_index_key(old_text_hash))

        pipeline.set(
            self._item_key(post.id),
            post.model_dump_json(),
            ex=REDIS_POST_ITEM_TTL_SECONDS,
        )
        pipeline.sadd(self.IDS_KEY, post.id)

        # сохраняем быстрый индекс news_id -> post_id
        pipeline.set(
            self._news_index_key(post.news_id),
            post.id,
            ex=REDIS_POST_ITEM_TTL_SECONDS,
        )

        # сохраняем индекс времени для pagination
        pipeline.zadd(
            self.CREATED_INDEX_KEY,
            {post.id: post.created_at.timestamp()},
        )

        # сохраняем быстрый индекс generated_text_hash -> post_id
        text_hash = generate_generated_text_hash(post.generated_text)
        pipeline.set(
            self._generated_text_index_key(text_hash),
            post.id,
            ex=REDIS_POST_ITEM_TTL_SECONDS,
        )

        pipeline.execute()

    def list_all(self) -> list[PostItem]:
        # читаем по zset индексу, новые сверху
        ids = self.redis.zrevrange(self.CREATED_INDEX_KEY, 0, -1)
        if not ids:
            return []

        pipeline = self.redis.pipeline()
        for post_id in ids:
            pipeline.get(self._item_key(post_id))

        payloads = pipeline.execute()

        result: list[PostItem] = []
        for payload in payloads:
            if not payload:
                continue
            result.append(PostItem.model_validate_json(payload))

        return result

    # добавлена пагинация
    def list_paginated(self, limit: int, offset: int) -> list[PostItem]:
        ids = self.redis.zrevrange(
            self.CREATED_INDEX_KEY,
            offset,
            offset + limit - 1,
        )
        if not ids:
            return []

        pipeline = self.redis.pipeline()
        for post_id in ids:
            pipeline.get(self._item_key(post_id))

        payloads = pipeline.execute()

        result: list[PostItem] = []
        for payload in payloads:
            if not payload:
                continue
            result.append(PostItem.model_validate_json(payload))

        return result

    def get_by_id(self, post_id: str) -> Optional[PostItem]:
        payload = self.redis.get(self._item_key(post_id))
        if not payload:
            return None

        return PostItem.model_validate_json(payload)

    def get_by_news_id(self, news_id: str) -> Optional[PostItem]:
        # lookup через отдельный индекс
        post_id = self.redis.get(self._news_index_key(news_id))
        if not post_id:
            return None

        return self.get_by_id(post_id)

    def get_by_generated_text(self, text: str) -> Optional[PostItem]:
        # быстрый lookup через отдельный индекс
        text_hash = generate_generated_text_hash(text)
        post_id = self.redis.get(self._generated_text_index_key(text_hash))
        if not post_id:
            return None

        post = self.get_by_id(post_id)
        if post is None:
            return None

        # дополнительная защитная проверка на случай коллизии hash
        if normalize_generated_text(post.generated_text) != normalize_generated_text(text):
            return None

        return post

    def list_publishable(self) -> list[PostItem]:
        return [
            item for item in self.list_all()
            if (
                    item.status == PostStatus.GENERATED
                    and item.published_at is None
                    and item.external_message_id is None
            )
        ]

    def update(self, post: PostItem) -> None:
        """Обновляет существующий пост по id."""
        existing = self.get_by_id(post.id)
        if existing is None:
            raise LookupError(f"Post not found: {post.id}")

        # обновляет все индексы
        self.save(post)

    def write_all(self, items: Iterable[PostItem]) -> None:
        """
        Полностью пересобирает Redis-хранилище постов.
        """
        items_list = list(items)
        existing_ids = self.redis.smembers(self.IDS_KEY)

        pipeline = self.redis.pipeline()

        # удаляем старые item-ключи и индексы
        for post_id in existing_ids:
            payload = self.redis.get(self._item_key(post_id))
            if payload:
                existing_post = PostItem.model_validate_json(payload)
                pipeline.delete(self._news_index_key(existing_post.news_id))

                # удаляем старый индекс generated_text
                old_text_hash = generate_generated_text_hash(existing_post.generated_text)
                pipeline.delete(self._generated_text_index_key(old_text_hash))

            pipeline.delete(self._item_key(post_id))

        pipeline.delete(self.IDS_KEY)
        pipeline.delete(self.CREATED_INDEX_KEY)

        for item in items_list:
            pipeline.set(
                self._item_key(item.id),
                item.model_dump_json(),
                ex=REDIS_POST_ITEM_TTL_SECONDS,
            )
            pipeline.sadd(self.IDS_KEY, item.id)

            # восстанавливаем индекс news_id -> post_id
            pipeline.set(
                self._news_index_key(item.news_id),
                item.id,
                ex=REDIS_POST_ITEM_TTL_SECONDS,
            )

            # восстанавливаем индекс времени
            pipeline.zadd(
                self.CREATED_INDEX_KEY,
                {item.id: item.created_at.timestamp()},
            )

            # восстанавливаем индекс generated_text -> post_id
            text_hash = generate_generated_text_hash(item.generated_text)
            pipeline.set(
                self._generated_text_index_key(text_hash),
                item.id,
                ex=REDIS_POST_ITEM_TTL_SECONDS,
            )

        pipeline.execute()

    # быстрый count по индексу ids
    def count_all(self) -> int:
        return self.redis.scard(self.IDS_KEY)
