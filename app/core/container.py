from __future__ import annotations

from functools import lru_cache

from app.news_parser.sites import (
    available_source_items,
    collect_from_sites,
    available_source_ids,
)
from app.services import (
    FilterService,
    GenerationService,
    KeywordService,
    LogService,
    NewsService,
    PostService,
    PublishService,
    SourceService,
)

from app.services.generation_service import build_post_generator
from app.storage import (
    get_keyword_storage,
    get_log_storage,
    get_news_storage,
    get_post_storage,
    get_source_storage,
)
from app.telegram.publisher import TelegramPublisher


class Container:
    """Централизованный контейнер зависимостей приложения."""

    def __init__(self) -> None:
        # storages
        self.news_storage = get_news_storage()
        self.post_storage = get_post_storage()
        self.source_storage = get_source_storage()
        self.keyword_storage = get_keyword_storage()
        self.log_storage = get_log_storage()

        # services
        self.log_service = LogService(storage=self.log_storage)

        self.keyword_service = KeywordService(storage=self.keyword_storage)

        self.source_service = SourceService(
            storage=self.source_storage,
            available_source_items_provider=available_source_items,
        )

        self.filter_service = FilterService(
            keyword_service=self.keyword_service,
            log_service=self.log_service,
            source_service=self.source_service,
        )

        self.news_service = NewsService(
            storage=self.news_storage,
            source_service=self.source_service,
            collector=collect_from_sites,
            available_sites_provider=available_source_ids,
            log_service=self.log_service,
        )

        self.post_service = PostService(storage=self.post_storage)

        self.generation_service = GenerationService(
            news_storage=self.news_storage,
            post_storage=self.post_storage,
            log_service=self.log_service,
            # Передаём новую фабрику из app.services.generation_service
            generator_factory=build_post_generator,
        )

        self.publish_service = PublishService(
            post_storage=self.post_storage,
            publisher=TelegramPublisher(),
            log_service=self.log_service,
        )


@lru_cache(maxsize=1)
def get_container() -> Container:
    """Возвращает singleton-контейнер для API и Celery-задач."""
    return Container()


def get_log_service() -> LogService:
    return get_container().log_service


def get_keyword_service() -> KeywordService:
    return get_container().keyword_service


def get_filter_service() -> FilterService:
    return get_container().filter_service


def get_source_service() -> SourceService:
    return get_container().source_service


def get_news_service() -> NewsService:
    return get_container().news_service


def get_post_service() -> PostService:
    return get_container().post_service


def get_generation_service() -> GenerationService:
    return get_container().generation_service


def get_publish_service() -> PublishService:
    return get_container().publish_service
