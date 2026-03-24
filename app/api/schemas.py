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
    processed_sites: List[str]
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


# --- Sources ---

class SourceItemResponse(BaseModel):
    id: str
    type: str
    name: str
    url: Optional[str]
    enabled: bool


class SourceCreateRequest(BaseModel):
    id: str = Field(min_length=1)
    type: str
    name: str = Field(min_length=1)
    url: Optional[str] = None
    enabled: bool = True

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("source id must not be empty")
        return normalized

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"site", "tg"}:
            raise ValueError("type must be site or tg")
        return normalized

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("source name must not be empty")
        return normalized

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: Optional[str]) -> Optional[str]:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None
        return normalized


class SourceListResponse(BaseModel):
    items: List[SourceItemResponse]
    total: int


class SourceUpdateRequest(BaseModel):
    enabled: bool


# --- Keyword management API ---
class KeywordItemResponse(BaseModel):
    value: str
    type: str


class KeywordListResponse(BaseModel):
    items: List[KeywordItemResponse]
    total: int


class KeywordCreateRequest(BaseModel):
    value: str = Field(min_length=1)
    type: int


class KeywordCreateRequest(BaseModel):
    value: str = Field(min_length=1)
    type: str

    @field_validator("value")
    @classmethod
    def validate_value(cls, value: str) -> str:
        normalized = value.strip().lower()
        if not normalized:
            raise ValueError("keyword value must not be empty")
        return normalized

    @field_validator("type")
    @classmethod
    def validate_type(cls, value: str) -> str:
        normalized = value.strip().lower()
        if normalized not in {"include", "exclude"}:
            raise ValueError("type must be include or exclude")
        return normalized


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
