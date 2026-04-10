from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.models import KeywordType, LogLevel, NewsStatus, PostStatus, SourceType


# --- Error ---

class ErrorPayload(BaseModel):
    type: str = Field(
        description="Application error type",
        examples=["ValidationError"],
    )
    message: str = Field(
        description="Human-readable error message",
        examples=["Invalid request data"],
    )
    details: list[dict[str, Any]] | None = Field(
        default=None,
        description="Optional validation or technical details",
    )


class ErrorResponse(BaseModel):
    error: ErrorPayload

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "error": {
                    "type": "ValidationError",
                    "message": "Invalid request data",
                    "details": [
                        {
                            "type": "string_too_short",
                            "loc": ["body", "text"],
                            "msg": "String should have at least 1 character",
                            "input": "",
                            "ctx": {"min_length": 1},
                        }
                    ],
                }
            }
        }
    )


# --- System ---

class HealthResponse(BaseModel):
    status: str = Field(
        description="Application health status",
        examples=["ok"],
    )
    storage_backend: str = Field(
        description="Configured storage backend",
        examples=["redis"],
    )
    llm_provider: str = Field(
        description="Configured LLM provider",
        examples=["gemini"],
    )
    redis_configured: bool = Field(
        description="Whether Redis URL is configured",
        examples=[True],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "status": "ok",
                "storage_backend": "redis",
                "llm_provider": "gemini",
                "redis_configured": True,
            }
        }
    )


# --- Collect ---

class CollectSitesRequest(BaseModel):
    sites: list[str] = Field(
        default_factory=lambda: ["habr"],
        description="List of source ids to collect news from",
        examples=[["habr", "vc"]],
    )
    limit_per_site: int = Field(
        default=20,
        ge=1,
        le=100,
        description="Maximum number of news items to collect per source",
        examples=[5],
    )

class CollectSitesResponse(BaseModel):
    requested_sites: list[str] = Field(
        description="Source ids requested by client",
        examples=[["habr", "vc"]],
    )
    processed_sites: list[str] = Field(
        description="Source ids actually processed",
        examples=[["habr", "vc"]],
    )
    collected: int = Field(
        description="Number of collected news items",
        examples=[10],
    )
    saved: int = Field(
        description="Number of saved news items",
        examples=[8],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "requested_sites": ["habr", "vc"],
                "processed_sites": ["habr", "vc"],
                "collected": 10,
                "saved": 8,
            }
        }
    )


# --- Generate ---

class GenerateRequest(BaseModel):
    text: str = Field(
        min_length=1,
        max_length=500,
        description="Input text for Telegram post generation",
        examples=["FastAPI released a new update with performance improvements."],
    )

    @field_validator("text")
    @classmethod
    def validate_text(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("text must not be empty")
        return normalized


class GenerateResponse(BaseModel):
    generated_text: str = Field(
        description="Generated Telegram-ready text",
        examples=["FastAPI стал ещё быстрее. Новый релиз улучшает производительность и делает разработку удобнее."],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "generated_text": "FastAPI стал ещё быстрее. Новый релиз улучшает производительность и делает разработку удобнее."
            }
        }
    )


class GenerateFromNewsRequest(BaseModel):
    news_id: str = Field(
        min_length=1,
        description="Existing news item id",
        examples=["19f5341ea6623d0fc131ca7635a02e18d2a83e70fcf4c5af3bf8e149c3d2b038"],
    )

    @field_validator("news_id")
    @classmethod
    def validate_news_id(cls, value: str) -> str:
        normalized = value.strip()
        if not normalized:
            raise ValueError("news_id must not be empty")
        return normalized


class GenerateFromNewsResponse(BaseModel):
    id: str = Field(
        description="Generated post id",
        examples=["post_001"],
    )
    news_id: str = Field(
        description="Source news id",
        examples=["19f5341ea6623d0fc131ca7635a02e18d2a83e70fcf4c5af3bf8e149c3d2b038"],
    )
    generated_text: str = Field(
        description="Generated Telegram-ready text",
        examples=["Короткий AI-пост по новости."],
    )
    status: PostStatus = Field(
        description="Current post status",
        examples=["generated"],
    )
    created_at: datetime = Field(
        description="Post creation datetime",
        examples=["2026-04-06T12:00:00Z"],
    )
    published_at: datetime | None = Field(
        default=None,
        description="Telegram publication datetime if already published",
        examples=["2026-04-06T12:30:00Z"],
    )
    source: str = Field(
        description="Source identifier",
        examples=["habr"],
    )
    provider: str = Field(
        description="LLM provider used for generation",
        examples=["gemini"],
    )
    external_message_id: str | None = Field(
        default=None,
        description="External Telegram message id after publishing",
        examples=["106"],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "id": "post_001",
                "news_id": "19f5341ea6623d0fc131ca7635a02e18d2a83e70fcf4c5af3bf8e149c3d2b038",
                "generated_text": "Короткий AI-пост по новости 🚀",
                "status": "generated",
                "created_at": "2026-04-06T12:00:00Z",
                "published_at": None,
                "source": "habr",
                "provider": "gemini",
                "external_message_id": None,
            }
        }
    )


# --- Sources ---

class SourceItemResponse(BaseModel):
    id: str = Field(
        description="Unique source id",
        examples=["habr"],
    )
    type: SourceType = Field(
        description="Source type",
        examples=["site"],
    )
    name: str = Field(
        description="Human-readable source name",
        examples=["Habr"],
    )
    url: str | None = Field(
        default=None,
        description="Source URL or Telegram link",
        examples=["https://habr.com/rss"],
    )
    enabled: bool = Field(
        description="Whether source is enabled",
        examples=[True],
    )


class SourceCreateRequest(BaseModel):
    id: str | None = Field(
        default=None,
        description="Optional custom source id",
        examples=["custom_source"],
    )
    type: str = Field(
        description="Source type: site or tg",
        examples=["site"],
    )
    name: str = Field(
        min_length=1,
        description="Human-readable source name",
        examples=["Habr"],
    )
    url: str | None = Field(
        default=None,
        description="Source URL or Telegram link",
        examples=["https://habr.com/rss"],
    )
    enabled: bool = Field(
        default=True,
        description="Whether source is enabled for collection",
        examples=[True],
    )

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
    items: list[SourceItemResponse] = Field(
        description="List of configured sources",
    )
    total: int = Field(
        description="Total number of sources",
        examples=[4],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "habr",
                        "type": "site",
                        "name": "Habr",
                        "url": "https://habr.com/rss",
                        "enabled": True,
                    }
                ],
                "total": 1,
            }
        }
    )


class SourceUpdateRequest(BaseModel):
    name: str | None = Field(
        default=None,
        description="Updated source name",
        examples=["Updated source name"],
    )
    url: str | None = Field(
        default=None,
        description="Updated source URL or Telegram link",
        examples=["https://example.com/rss"],
    )
    enabled: bool | None = Field(
        default=None,
        description="Updated enabled flag",
        examples=[True],
    )

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


# --- Keywords ---


class KeywordItemResponse(BaseModel):
    value: str = Field(
        description="Keyword value",
        examples=["ai"],
    )
    type: KeywordType = Field(
        description="Keyword type",
        examples=["include"],
    )


class KeywordListResponse(BaseModel):
    items: list[KeywordItemResponse] = Field(
        description="List of filtering keywords",
    )
    total: int = Field(
        description="Total number of keywords",
        examples=[2],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {"value": "ai", "type": "include"},
                    {"value": "crypto", "type": "exclude"},
                ],
                "total": 2,
            }
        }
    )


class KeywordCreateRequest(BaseModel):
    value: str = Field(
        min_length=1,
        description="Keyword value",
        examples=["ai"],
    )
    type: str = Field(
        description="Keyword type: include or exclude",
        examples=["include"],
    )

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
    id: str = Field(
        description="Post id",
        examples=["post_001"],
    )
    news_id: str = Field(
        description="Source news id",
        examples=["news_001"],
    )
    generated_text: str = Field(
        description="Generated Telegram post text",
        examples=["AI сгенерировал краткий текст для публикации 🚀"],
    )
    status: PostStatus = Field(
        description="Current post status",
        examples=["published"],
    )
    created_at: datetime = Field(
        description="Post creation datetime",
        examples=["2026-04-06T12:00:00Z"],
    )
    published_at: datetime | None = Field(
        default=None,
        description="Publication datetime if published",
        examples=["2026-04-06T12:30:00Z"],
    )
    source: str = Field(
        description="Source identifier",
        examples=["habr"],
    )
    provider: str = Field(
        description="LLM provider used",
        examples=["gemini"],
    )
    external_message_id: str | None = Field(
        default=None,
        description="External Telegram message id",
        examples=["106"],
    )


class PostHistoryListResponse(BaseModel):
    items: list[PostHistoryItemResponse] = Field(
        description="List of generated posts",
    )
    total: int = Field(
        description="Total number of posts",
        examples=[1],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "post_001",
                        "news_id": "news_001",
                        "generated_text": "AI сгенерировал краткий текст для публикации.",
                        "status": "published",
                        "created_at": "2026-04-06T12:00:00Z",
                        "published_at": "2026-04-06T12:30:00Z",
                        "source": "habr",
                        "provider": "gemini",
                        "external_message_id": "106",
                    }
                ],
                "total": 1,
            }
        }
    )


# --- Logs ---

class LogItemResponse(BaseModel):
    id: str = Field(
        description="Log record id",
        examples=["278e5c7c-d32b-49a8-b5f4-3dd044442739"],
    )
    created_at: datetime = Field(
        description="Log creation datetime",
        examples=["2026-04-02T10:31:38.525742Z"],
    )
    level: LogLevel = Field(
        description="Log level",
        examples=["info"],
    )
    message: str = Field(
        description="Log message",
        examples=["Publish task completed"],
    )
    source: str | None = Field(
        default=None,
        description="Component that produced the log",
        examples=["tasks.publish_posts_task"],
    )
    context: dict[str, Any] | None = Field(
        default=None,
        description="Structured log context",
    )


class LogListResponse(BaseModel):
    items: list[LogItemResponse] = Field(
        description="List of log records",
    )
    total: int = Field(
        description="Total number of returned log records",
        examples=[1],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "278e5c7c-d32b-49a8-b5f4-3dd044442739",
                        "created_at": "2026-04-02T10:31:38.525742Z",
                        "level": "info",
                        "message": "Publish task completed",
                        "source": "tasks.publish_posts_task",
                        "context": {"total": 4, "published": 4},
                    }
                ],
                "total": 1,
            }
        }
    )


# --- News ---

class NewsItemResponse(BaseModel):
    id: str = Field(
        description="News item id",
        examples=["news_001"],
    )
    title: str = Field(
        description="News title",
        examples=["FastAPI released a new version"],
    )
    summary: str = Field(
        description="Short news summary",
        examples=["The new release improves performance and developer experience."],
    )
    url: str | None = Field(
        default=None,
        description="Original news URL",
        examples=["https://example.com/news/fastapi-release"],
    )
    source: str = Field(
        description="Source identifier",
        examples=["habr"],
    )
    status: NewsStatus = Field(
        description="Current news processing status",
        examples=["filtered"],
    )
    published_at: datetime = Field(
        description="Original publication datetime",
        examples=["2026-04-06T09:00:00Z"],
    )


class NewsListResponse(BaseModel):
    items: list[NewsItemResponse] = Field(
        description="List of collected news items",
    )
    total: int = Field(
        description="Total number of news items",
        examples=[1],
    )

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "items": [
                    {
                        "id": "news_001",
                        "title": "FastAPI released a new version",
                        "summary": "The new release improves performance and developer experience.",
                        "url": "https://example.com/news/fastapi-release",
                        "source": "habr",
                        "status": "filtered",
                        "published_at": "2026-04-06T09:00:00Z",
                    }
                ],
                "total": 1,
            }
        }
    )
