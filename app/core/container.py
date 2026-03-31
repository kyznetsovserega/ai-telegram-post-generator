from __future__ import annotations

from functools import lru_cache

from app.ai.factory import build_text_generation_client
from app.ai.generator import PostGenerator
from app.news_parser.sites import (
    available_sites,
    available_source_items,
    collect_from_sites, available_source_ids,
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
from app.storage import (
    get_keyword_storage,
    get_log_storage,
    get_news_storage,
    get_post_storage,
    get_source_storage,
)
from app.telegram.publisher import TelegramPublisher


def build_post_generator() -> PostGenerator:
    """
    Создаём PostGenerator через factory AI-клиента.
    """
    return PostGenerator(client=build_text_generation_client())


class Container:
    """
    Централизованный контейнер зависимостей приложения.
    """

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

        self.filter_service = FilterService(
            keyword_service=self.keyword_service,
            log_service=self.log_service,
        )

        self.source_service = SourceService(
            storage=self.source_storage,
            available_source_items_provider=available_source_items,
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
            generator_factory=build_post_generator,
        )

        self.publish_service = PublishService(
            post_storage=self.post_storage,
            publisher=TelegramPublisher(),
            log_service=self.log_service,
        )


@lru_cache(maxsize=1)
def get_container() -> Container:
    """
    Singleton container для API и Celery-задач.
    """
    return Container()
