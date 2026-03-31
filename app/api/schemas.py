from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, field_validator
from app.models import KeywordType, LogLevel, PostStatus, SourceType


# --- Error ---
class ErrorPayload(BaseModel):
    type: str
    message: str
    details: list[dict[str, Any]] | None = None


class ErrorResponse(BaseModel):
    error: ErrorPayload


# --- Collect ---

class CollectSitesRequest(BaseModel):
    sites: list[str] = Field(default_factory=lambda: ["habr"])
    limit_per_site: int = Field(default=20, ge=1, le=100)


class CollectSitesResponse(BaseModel):
    requested_sites: list[str]
    processed_sites: list[str]
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
    status: PostStatus
    created_at: datetime
    published_at: datetime | None
    source: str
    provider: str
    external_message_id: str | None


# --- Sources ---

class SourceItemResponse(BaseModel):
    id: str
    type: SourceType
    name: str
    url: str | None
    enabled: bool


class SourceCreateRequest(BaseModel):
    id: str | None = None
    type: str
    name: str = Field(min_length=1)
    url: str | None = None
    enabled: bool = True

    @field_validator("id")
    @classmethod
    def validate_id(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip().lower()
        if not normalized:
            return None
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
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None
        return normalized


class SourceListResponse(BaseModel):
    items: list[SourceItemResponse]
    total: int


class SourceUpdateRequest(BaseModel):
    name: str | None = None
    url: str | None = None
    enabled: bool | None = None

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return value

        normalized = value.strip()
        if not normalized:
            raise ValueError("name must not be empty")

        return normalized

    @field_validator("url")
    @classmethod
    def validate_url(cls, value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        if not normalized:
            return None

        return normalized


# --- Keyword management API ---
class KeywordItemResponse(BaseModel):
    value: str
    type: KeywordType


class KeywordListResponse(BaseModel):
    items: list[KeywordItemResponse]
    total: int


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
    status: PostStatus
    created_at: datetime
    published_at: datetime | None
    source: str
    provider: str
    external_message_id: str | None


class PostHistoryListResponse(BaseModel):
    items: list[PostHistoryItemResponse]
    total: int


# --- Logs ---

class LogItemResponse(BaseModel):
    id: str
    created_at: datetime
    level: LogLevel
    message: str
    source: str | None
    context: dict[str, Any] | None


class LogListResponse(BaseModel):
    items: list[LogItemResponse]
    total: int


# --- News ---

class NewsItemResponse(BaseModel):
    id: str
    title: str
    summary: str
    url: str | None
    source: str
    status: str
    published_at: datetime


class NewsListResponse(BaseModel):
    items: list[NewsItemResponse]
    total: int
