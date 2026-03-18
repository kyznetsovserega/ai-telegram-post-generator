from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Optional, Any
from uuid import uuid4

from pydantic import BaseModel, Field, field_validator


def utc_now() -> datetime:
    """
    Возвращает дату и время в формате UTC
    с учетом часового пояса.
    """
    return datetime.now(timezone.utc)


class NewsStatus(str, Enum):
    """Статус обработки новости внутри pipeline."""
    NEW = "new"
    FILTERED = "filtered"
    DROPPED = "dropped"
    GENERATED = "generated"


class NewsItem(BaseModel):
    """Нормализованный объект новостей, сохраняемый после анализа."""
    id: str
    title: str
    url: Optional[str] = None
    summary: str
    source: str
    published_at: datetime
    raw_text: Optional[str] = None
    status: NewsStatus = NewsStatus.NEW

    @field_validator("status",mode="before")
    @classmethod
    def normalize_news_status(cls,value:Any) -> Any:
        if isinstance(value,str):
            return value.strip().lower()
        return value


class PostStatus(str, Enum):
    """ Статус жизненного цикла созданных сообщений. """
    NEW = "new"
    GENERATED = "generated"
    PUBLISHED = "published"
    FAILED = "failed"


class PostItem(BaseModel):
    """ Создан пост в Telegram на основе исходной новости. """
    id: str = Field(default_factory=lambda: str(uuid4()))
    news_id: str
    generated_text: str
    status: PostStatus = PostStatus.GENERATED
    published_at: Optional[datetime] = None
    created_at: datetime = Field(default_factory=utc_now)

    source: str
    provider: str
    external_message_id: Optional[str] = None

    @field_validator("status",mode="before")
    @classmethod
    def normalize_post_status(cls,value:Any) -> Any:
        if isinstance(value,str):
            return value.strip().lower()
        return value
