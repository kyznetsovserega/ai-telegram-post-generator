from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from uuid import uuid4

from app import config
from app.ai.factory import build_text_generation_client
from app.ai.generator import PostGenerator
from app.models import LogItem, LogLevel, NewsItem, PostItem, PostStatus
from app.services.log_service import LogService

GeneratorFactory = Callable[[], PostGenerator]


def build_post_generator() -> PostGenerator:
    """Создаёт генератор постов с текущим LLM client."""
    client = build_text_generation_client()
    return PostGenerator(client=client)


class GenerationService:
    """Сервис генерации Telegram-постов."""

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
    def ensure_provider_configured() -> str:
        provider = config.LLM_PROVIDER.lower()

        if provider == "openai" and not config.OPENAI_API_KEY:
            raise RuntimeError("OPENAI_API_KEY is not configured")

        if provider == "gemini" and not config.GEMINI_API_KEY:
            raise RuntimeError("GEMINI_API_KEY is not configured")

        return provider

    async def generate_from_text(self, text: str) -> str:
        self.ensure_provider_configured()

        generator = self.generator_factory()
        post = await generator.generate_from_text(text)
        return post.text

    async def generate_from_news(self, news_id: str) -> PostItem:
        provider = self.ensure_provider_configured()

        news_item = self.news_storage.get_by_id(news_id)
        if news_item is None:
            raise LookupError(f"News item with id='{news_id}' not found")

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

        generator = self.generator_factory()
        generated_post = await generator.generate_from_news(news_item)

        existing_text_post = self.post_storage.get_by_generated_text(generated_post.text)
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

    async def generate_for_news_items(
            self,
            items: list[NewsItem],
    ) -> dict[str, int]:
        """
        Пакетная генерация постов для списка новостей.

        Логика намеренно простая:
        - если пост по news_id уже есть, считаем как skipped
        - если генерация завершилась ошибкой, считаем как failed
        - если сервис вернул пост не для текущего news_id
          (например, из-за дедупликации по тексту), считаем как skipped
        - только реально созданный пост для текущей новости считаем generated
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
                post_item = await self.generate_from_news(item.id)
            except Exception as exc:
                summary["failed"] += 1

                self.log_service.add_log(
                    LogItem(
                        level=LogLevel.ERROR,
                        message="Batch generation failed",
                        source="generation_service",
                        context={
                            "news_id": item.id,
                            "news_source": item.source,
                            "reason": str(exc),
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
