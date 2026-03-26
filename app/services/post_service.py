from __future__ import annotations

from app.models import PostItem


class PostService:
    """Сервис работы с историей сгенерированных постов."""

    def __init__(self, storage):
        self.storage = storage

    def list_all(self) -> list[PostItem]:
        return self.storage.list_all()
