from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from app import config
from app.ai.factory import build_text_generation_client
from app.ai.generator import PostGenerator
from app.models import PostItem, PostStatus
from app.storage.news import JsonlNewsStorage
from app.storage.posts import JsonlPostStorage


class GenerationService:
    """Сервис генерации Telegram-постов."""

    def __init__(
            self,
            news_storage_path: str | Path = "data/news.jsonl",
            post_storage_path: str | Path = "data/posts.jsonl",
    ) -> None:
        self.news_storage = JsonlNewsStorage(path=Path(news_storage_path))
        self.post_storage = JsonlPostStorage(file_path=Path(post_storage_path))

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

        client = build_text_generation_client()
        generator = PostGenerator(client=client)
        post = await generator.generate_from_text(text)

        return post.text

    async def generate_from_news(self, news_id: str) -> PostItem:
        provider = self.ensure_provider_configured()

        news_item = self.news_storage.get_by_id(news_id)
        if news_item is None:
            raise LookupError(f"News item with id='{news_id}' not found")

        existing_post = self.post_storage.get_by_news_id(news_item.id)
        if existing_post is not None:
            return existing_post

        client = build_text_generation_client()
        generator = PostGenerator(client=client)
        generated_post = await generator.generate_from_news(news_item)

        existing_text_post = self.post_storage.get_by_generated_text(generated_post.text)
        if existing_text_post is not None:
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
        return post_item
