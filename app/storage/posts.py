from __future__ import annotations

import json
from pathlib import Path
from typing import Optional

from app.models import PostItem


class JsonlPostStorage:
    """ JSONL-хранилище для сгенерированных сообщений Telegram. """

    def __init__(self, file_path: str | Path = "data/posts.jsonl") -> None:
        self.file_path = Path(file_path)
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, post: PostItem) -> None:
        """ Добавление сгенерированного сообщения в файл JSONL. """
        with self.file_path.open("a", encoding="utf-8") as file:
            file.write(post.model_dump_json() + "\n")

    def list_all(self) -> list[PostItem]:
        """ Возврат всех сохраненных новостей. """
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
        """ Вернуть новость по ее id. """
        for item in self.list_all():
            if item.id == news_id:
                return item
        return None

    def get_by_news_id(self, news_id: str) -> Optional[PostItem]:
        """Return the first post generated from a given news item."""
        for item in self.list_all():
            if item.news_id == news_id:
                return item
        return None
