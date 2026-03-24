from __future__ import annotations

from app.models import PostItem
from app.storage import get_post_storage


class PostService:
    """Сервис работы с историей сгенерированных постов."""

    def __init__(self) -> None:
        self.storage = get_post_storage()

    def list_all(self) -> list[PostItem]:
        return self.storage.list_all()
