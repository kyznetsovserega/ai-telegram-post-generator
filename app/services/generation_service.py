from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from app import config
from app.ai.errors import AiRateLimitError, AiTemporaryUnavailableError
from app.ai.factory import build_text_generation_client
from app.ai.generator import PostGenerator
from app.models import LogItem, LogLevel, NewsItem, PostItem, PostStatus
from app.services.log_service import LogService

GeneratorFactory = Callable[[str], PostGenerator]


def build_post_generator(provider: str) -> PostGenerator:
    """Создаёт генератор постов с явным LLM provider."""
    # передаём provider явно в фабрику
    client = build_text_generation_client(provider)
    return PostGenerator(client=client)


class GenerationService:
    """
    Сервис генерации Telegram-постов.

    Отвечает за:
    - генерацию постов через LLM;
    - дедупликацию (по news_id и тексту);
    - batch-генерацию;
    - логирование.
    """

    def __init__(
            self,
            news_storage=None,
            post_storage=None,
            log_service: LogService | None = None,
            generator_factory: GeneratorFactory = build_post_generator,
    ) -> None:
        self.news_storage = news_storage
        self.post_storage = post_storage
        self.log_service = log_service
        self.generator_factory = generator_factory

    @staticmethod
    def resolve_provider() -> str:
        """
        Выбирает доступный LLM-провайдер с fallback логикой.

        Приоритет:
        1. provider из LLM_PROVIDER
        2. openai
        3. gemini
        4. free_llm
        """
        requested_provider = config.LLM_PROVIDER.lower().strip()

        provider_checks = {
            "openai": bool(config.OPENAI_API_KEY),
            "gemini": bool(config.GEMINI_API_KEY),
            "free_llm": bool(config.FREE_LLM_API_KEY),
        }

        # Если пользователь явно указал провайдера и он настроен — используем его.
        if requested_provider in provider_checks and provider_checks[requested_provider]:
            return requested_provider

        # Если выбранный provider не настроен — автоматически fallback на доступный.
        for provider in ("openai", "gemini", "free_llm"):
            if provider_checks[provider]:
                return provider

        raise RuntimeError(
            "No LLM provider configured. "
            "Set one of: OPENAI_API_KEY / GEMINI_API_KEY / FREE_LLM_API_KEY"
        )

    async def generate_from_text(self, text: str) -> str:
        """
        Генерация поста из произвольного текста (API-слой).
        """
        provider = self.resolve_provider()

        # передаём provider в фабрику генератора
        generator = self.generator_factory(provider)
        post = await generator.generate_from_text(text)
        return post.text

    async def generate_from_news(self, news_id: str) -> PostItem:
        """
        Генерация поста по news_id (API-слой).
        """
        news_item = self.news_storage.get_by_id(news_id)
        if news_item is None:
            raise LookupError(f"News item with id='{news_id}' not found")

        return await self._generate_from_news_item(news_item)

    async def generate_for_news_items(
            self,
            items: list[NewsItem],
    ) -> dict[str, int]:
        """
        Пакетная генерация постов.

        Правила:
        - уже есть пост → skipped
        - ошибка → failed
        - дедуп текста → skipped
        - новый пост → generated
        """
        summary = {
            "total": len(items),
            "generated": 0,
            "skipped": 0,
            "failed": 0,
        }

        for item in items:
            existing_post = self.post_storage.get_by_news_id(item.id)
            if existing_post is not None:
                summary["skipped"] += 1

                self.log_service.add_log(
                    LogItem(
                        level=LogLevel.INFO,
                        message="Batch generation skipped because post already exists",
                        source="generation_service",
                        context={
                            "news_id": item.id,
                            "post_id": existing_post.id,
                            "provider": existing_post.provider,
                        },
                    )
                )
                continue

            try:
                post_item = await self._generate_from_news_item(item)

            # Отдельно классифицируем rate limit
            except AiRateLimitError as exc:
                summary["failed"] += 1

                self.log_service.add_log(
                    LogItem(
                        level=LogLevel.ERROR,
                        message="Batch generation failed due to rate limit",
                        source="generation_service",
                        context={
                            "news_id": item.id,
                            "news_source": item.source,
                            "reason": "rate_limit",
                            "details": str(exc),
                            "exception_type": type(exc).__name__,
                        },
                    )
                )
                continue

            # Отдельно логируем временную недоступность провайдера
            except AiTemporaryUnavailableError as exc:
                summary["failed"] += 1

                self.log_service.add_log(
                    LogItem(
                        level=LogLevel.ERROR,
                        message="Batch generation failed because provider is temporarily unavailable",
                        source="generation_service",
                        context={
                            "news_id": item.id,
                            "news_source": item.source,
                            "reason": "temporary_unavailable",
                            "details": str(exc),
                            "exception_type": type(exc).__name__,
                        },
                    )
                )
                continue

            except Exception as exc:
                summary["failed"] += 1

                self.log_service.add_log(
                    LogItem(
                        level=LogLevel.ERROR,
                        message="Batch generation failed with unexpected error",
                        source="generation_service",
                        context={
                            "news_id": item.id,
                            "news_source": item.source,
                            "reason": "unexpected_error",
                            "details": str(exc),
                            "exception_type": type(exc).__name__,
                        },
                    )
                )
                continue

            if post_item.news_id == item.id:
                summary["generated"] += 1
            else:
                summary["skipped"] += 1

                self.log_service.add_log(
                    LogItem(
                        level=LogLevel.INFO,
                        message="Batch generation skipped because another post was reused",
                        source="generation_service",
                        context={
                            "requested_news_id": item.id,
                            "returned_news_id": post_item.news_id,
                            "post_id": post_item.id,
                            "provider": post_item.provider,
                        },
                    )
                )

        return summary

    async def _generate_from_news_item(self, news_item: NewsItem) -> PostItem:
        """
        Общая логика генерации поста по новости.
        """
        provider = self.resolve_provider()

        existing_post = self.post_storage.get_by_news_id(news_item.id)
        if existing_post is not None:
            self.log_service.add_log(
                LogItem(
                    level=LogLevel.INFO,
                    message="Generation skipped because post already exists",
                    source="generation_service",
                    context={
                        "news_id": news_item.id,
                        "post_id": existing_post.id,
                        "provider": existing_post.provider,
                    },
                )
            )
            return existing_post

        # создаём generator под конкретный provider
        generator = self.generator_factory(provider)
        generated_post = await generator.generate_from_news(news_item)

        existing_text_post = self.post_storage.get_by_generated_text(
            generated_post.text
        )
        if existing_text_post is not None:
            self.log_service.add_log(
                LogItem(
                    level=LogLevel.INFO,
                    message="Generation skipped because duplicate generated text already exists",
                    source="generation_service",
                    context={
                        "news_id": news_item.id,
                        "existing_post_id": existing_text_post.id,
                        "existing_news_id": existing_text_post.news_id,
                        "provider": existing_text_post.provider,
                    },
                )
            )
            return existing_text_post

        post_item = PostItem(
            id=str(uuid4()),
            news_id=news_item.id,
            generated_text=generated_post.text,
            status=PostStatus.GENERATED,
            created_at=datetime.now(timezone.utc),
            published_at=None,
            source=news_item.source,
            provider=provider,
        )

        self.post_storage.save(post_item)

        self.log_service.add_log(
            LogItem(
                level=LogLevel.INFO,
                message="Post generated successfully",
                source="generation_service",
                context={
                    "post_id": post_item.id,
                    "news_id": news_item.id,
                    "provider": provider,
                    "news_source": news_item.source,
                },
            )
        )
        return post_item
