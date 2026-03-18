from __future__ import annotations
from dataclasses import dataclass

from app.config import TELEGRAM_CHANNEL


@dataclass(frozen=True, slots=True)
class PublishResult:
    is_published: bool
    external_id: str | None = None
    error_message:str | None=None


class TelegramPublisher:
    """
    MVP-обёртка над Telegram publishing.
    """

    def publish_post(self, text: str) -> PublishResult:
        normalized = text.strip()

        if not normalized:
            raise ValueError("Post text must not be empty")

        if not TELEGRAM_CHANNEL.strip():
            raise RuntimeError("TELEGRAM_CHANNEL is not configured")

        # MVP-заглушка
        return PublishResult(
            is_published=True,
            external_id=None,
            error_message=None,
        )
