from __future__ import annotations

from pathlib import Path

from app.models import PostItem
from app.storage.posts import JsonlPostStorage


class PostService:
    """Сервис работы с историей сгенерированных постов."""

    def __init__(self, storage_path: str | Path = "data/posts.jsonl") -> None:
        self.storage = JsonlPostStorage(file_path=Path(storage_path))

    def list_all(self) -> list[PostItem]:
        return self.storage.list_all()
