from __future__ import annotations

from app.services import GenerationService, KeywordService, NewsService, PostService
from app.services.log_service import LogService
from app.services.source_service import SourceService


def get_source_service() -> SourceService:
    return SourceService()


def get_keyword_service() -> KeywordService:
    return KeywordService()


def get_generation_service() -> GenerationService:
    return GenerationService()


def get_news_service() -> NewsService:
    return NewsService()


def get_post_service() -> PostService:
    return PostService()


def get_log_service() -> LogService:
    return LogService()
