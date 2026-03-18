from __future__ import annotations

import asyncio
from dataclasses import dataclass

from telethon import TelegramClient

from app.config import (
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_CHANNEL,
    TELEGRAM_SESSION_NAME,
)


@dataclass(frozen=True, slots=True)
class PublishResult:
    is_published: bool
    external_id: str | None = None
    error_message:str | None=None


class TelegramPublisher:
    """
    MVP-обёртка над Telegram publishing через Telethon.
    """

    def publish_post(self, text: str) -> PublishResult:
        return asyncio.run(self.publish_post_async(text))

    async def publish_post_async(self,text:str) -> PublishResult:
        normalized = text.strip()

        if not normalized:
            raise ValueError("Post text must not be empty")

        if not TELEGRAM_CHANNEL.strip():
            raise RuntimeError("TELEGRAM_CHANNEL is not configured")

        if not TELEGRAM_API_ID.strip():
            raise RuntimeError("TELEGRAM_API_ID is not configured")

        if not TELEGRAM_API_HASH.strip():
            raise RuntimeError("TELEGRAM_API_HASH is not configured")

        client=TelegramClient(
            session=TELEGRAM_SESSION_NAME,
            api_id=int(TELEGRAM_API_ID),
            api_hash=TELEGRAM_API_HASH,
        )

        async with client:
            # Пока это только техническая проверка:
            # конфиг валиден, клиент может быть создан.
            return PublishResult(
                is_published=True,
                external_id=None,
                error_message=None,
            )
