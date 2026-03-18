from __future__ import annotations

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field, field_validator


# --- Collect ---

class CollectSitesRequest(BaseModel):
    sites: List[str] = Field(default_factory=lambda: ["habr"])
    limit_per_site: int = Field(default=20, ge=1, le=100)


class CollectSitesResponse(BaseModel):
    requested_sites: List[str]
    collected: int
    saved: int


# --- Generate ---

class GenerateRequest(BaseModel):
    """ Ручной ввод текста и генерация поста. """
    text: str = Field(min_length=1, max_length=500)

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text must not be empty")
        return normalized


class GenerateResponse(BaseModel):
    generated_text: str


class GenerateFromNewsRequest(BaseModel):
    news_id: str = Field(min_length=1)

    @field_validator("news_id")
    @classmethod
    def validate_news_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("news_id must not be empty")
        return normalized


class GenerateFromNewsResponse(BaseModel):
    id: str
    news_id: str
    generated_text: str
    status: str
    created_at: datetime
    published_at: Optional[datetime]
    source: str
    provider: str
    external_message_id: Optional[str]


# --- Posts history ---

class PostHistoryItemResponse(BaseModel):
    id: str
    news_id: str
    generated_text: str
    status: str
    created_at: datetime
    published_at: Optional[datetime]
    source: str
    provider: str
    external_message_id: Optional[str]


class PostHistoryListResponse(BaseModel):
    items: List[PostHistoryItemResponse]
    total: int
