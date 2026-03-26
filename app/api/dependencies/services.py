from __future__ import annotations

from app.services import (
    GenerationService,
    KeywordService,
    NewsService,
    PostService,
    PublishService,
    SourceService,
    LogService,
    FilterService,
)

from app.storage import (
    get_news_storage,
    get_post_storage,
    get_keyword_storage,
    get_source_storage,
    get_log_storage,
)

from app.news_parser.sites import collect_from_sites, available_sites, available_source_items
from app.ai.generator import PostGenerator
from app.ai.factory import build_text_generation_client
from app.telegram.publisher import TelegramPublisher


def build_post_generator():
    return PostGenerator(client=build_text_generation_client())


def get_log_service():
    return LogService(storage=get_log_storage())


def get_keyword_service():
    return KeywordService(storage=get_keyword_storage())


def get_filter_service():
    return FilterService(
        keyword_service=get_keyword_service(),
    )


def get_source_service():
    return SourceService(
        storage=get_source_storage(),
        available_source_items_provider=available_source_items,
    )


def get_news_service():
    return NewsService(
        storage=get_news_storage(),
        source_service=get_source_service(),
        collector=collect_from_sites,
        available_sites_provider=available_sites,
    )


def get_post_service():
    return PostService(storage=get_post_storage())


def get_generation_service():
    return GenerationService(
        news_storage=get_news_storage(),
        post_storage=get_post_storage(),
        log_service=get_log_service(),
        generator_factory=build_post_generator,
    )


def get_publish_service():
    return PublishService(
        post_storage=get_post_storage(),
        publisher=TelegramPublisher(),
        log_service=get_log_service(),
    )
