from __future__ import annotations

from dataclasses import dataclass

from telethon.sync import TelegramClient

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
    error_message: str | None = None


class TelegramPublisher:
    """ Sync-first publisher для Celery. """

    def publish_post(self, text: str) -> PublishResult:
        normalized = text.strip()

        if not normalized:
            raise ValueError("Post text must not be empty")

        if not TELEGRAM_CHANNEL.strip():
            raise RuntimeError("TELEGRAM_CHANNEL is not configured")

        if not TELEGRAM_API_ID:
            raise RuntimeError("TELEGRAM_API_ID is not configured")

        if not TELEGRAM_API_HASH:
            raise RuntimeError("TELEGRAM_API_HASH is not configured")

        try:
            # sync Telethon клиент
            with TelegramClient(
                    session=TELEGRAM_SESSION_NAME,
                    api_id=int(TELEGRAM_API_ID),
                    api_hash=TELEGRAM_API_HASH,
            ) as client:

                message = client.send_message(
                    TELEGRAM_CHANNEL,
                    normalized,
                )

                return PublishResult(
                    is_published=True,
                    external_id=str(message.id),
                    error_message=None,
                )

        except Exception as exc:
            return PublishResult(
                is_published=False,
                external_id=None,
                error_message=str(exc),
            )
