from __future__ import annotations

from app.models import PostItem


class PostService:
    """Сервис работы с историей сгенерированных постов."""

    def __init__(self, storage):
        self.storage = storage

    def list_all(self) -> list[PostItem]:
        return self.storage.list_all()

    def get_by_news_id(self, news_id: str) -> PostItem | None:
        return self.storage.get_by_news_id(news_id)

    def get_by_generated_text(self, text: str) -> PostItem | None:
        return self.storage.get_by_generated_text(text)

    def list_publishable(self) -> list[PostItem]:
        return self.storage.list_publishable()

    def update(self, post: PostItem) -> None:
        self.storage.update(post)
