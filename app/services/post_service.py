from __future__ import annotations

from app.models import PostItem


class PostService:
    """Сервис работы с постами."""

    def __init__(self, storage):
        self.storage = storage

    def list_all(self) -> list[PostItem]:
        return self.storage.list_all()

    # пагинацию на уровне service
    def list_paginated(self, limit: int, offset: int) -> list[PostItem]:
        if hasattr(self.storage, "list_paginated"):
            return self.storage.list_paginated(limit=limit, offset=offset)

        items = self.storage.list_all()
        return items[offset: offset + limit]

    # total-count для API pagination
    def count_all(self) -> int:
        if hasattr(self.storage, "count_all"):
            return self.storage.count_all()

        return len(self.storage.list_all())

    def get_by_news_id(self, news_id: str) -> PostItem | None:
        return self.storage.get_by_news_id(news_id)

    def get_by_generated_text(self, text: str) -> PostItem | None:
        return self.storage.get_by_generated_text(text)

    def list_publishable(self) -> list[PostItem]:
        return self.storage.list_publishable()

    def update(self, post: PostItem) -> None:
        self.storage.update(post)
