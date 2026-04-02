from __future__ import annotations

import json
from pathlib import Path
from typing import Optional, Iterable

from app.config import REDIS_POST_ITEM_TTL_SECONDS
from app.models import PostItem, PostStatus
from app.storage.redis_client import get_redis_client


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

        return result

    def get_by_id(self, news_id: str) -> Optional[PostItem]:
        """Возвращает пост по его id."""
        for item in self.list_all():
            if item.id == news_id:
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
        normalized = text.strip()

        for item in self.list_all():
            if item.generated_text.strip() == normalized:
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


class RedisPostStorage:
    """Redis-хранилище для сгенерированных сообщений Telegram."""

    IDS_KEY = "posts:ids"
    ITEM_KEY_PREFIX = "posts:item:"

    def __init__(self) -> None:
        self.redis = get_redis_client()

    @classmethod
    def _item_key(cls, post_id: str) -> str:
        return f"{cls.ITEM_KEY_PREFIX}{post_id}"

    def save(self, post: PostItem) -> None:
        pipeline = self.redis.pipeline()

        pipeline.set(
            self._item_key(post.id),
            post.model_dump_json(),
            ex=REDIS_POST_ITEM_TTL_SECONDS,
        )
        pipeline.sadd(self.IDS_KEY, post.id)
        pipeline.execute()

    def list_all(self) -> list[PostItem]:
        ids = sorted(self.redis.smembers(self.IDS_KEY))
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
        for item in self.list_all():
            if item.news_id == news_id:
                return item
        return None

    def get_by_generated_text(self, text: str) -> Optional[PostItem]:
        normalized = text.strip()

        for item in self.list_all():
            if item.generated_text.strip() == normalized:
                return item
        return None

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

        self.save(post)

    def write_all(self, items: Iterable[PostItem]) -> None:
        """
        Полностью пересобирает Redis-хранилище постов.
        """
        items_list = list(items)
        existing_ids = self.redis.smembers(self.IDS_KEY)

        pipeline = self.redis.pipeline()

        for post_id in existing_ids:
            pipeline.delete(self._item_key(post_id))

        pipeline.delete(self.IDS_KEY)

        for item in items_list:
            pipeline.set(
                self._item_key(item.id),
                item.model_dump_json(),
                ex=REDIS_POST_ITEM_TTL_SECONDS,
            )
            pipeline.sadd(self.IDS_KEY, item.id)

        pipeline.execute()
