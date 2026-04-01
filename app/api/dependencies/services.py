from __future__ import annotations

from app.core.container import get_container


def get_log_service():
    """Dependency: LogService."""
    return get_container().log_service


def get_keyword_service():
    """Dependency: KeywordService."""
    return get_container().keyword_service


def get_filter_service():
    """Dependency: FilterService."""
    return get_container().filter_service


def get_source_service():
    """Dependency: SourceService."""
    return get_container().source_service


def get_news_service():
    """Dependency: NewsService."""
    return get_container().news_service


def get_post_service():
    """Dependency: PostService."""
    return get_container().post_service


def get_generation_service():
    """Dependency: GenerationService."""
    return get_container().generation_service


def get_publish_service():
    """Dependency: PublishService."""
    return get_container().publish_service
