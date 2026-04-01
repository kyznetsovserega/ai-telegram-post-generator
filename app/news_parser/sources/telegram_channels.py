from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from telethon import TelegramClient
from telethon.tl.custom.message import Message

from app.config import (
    TELEGRAM_API_HASH,
    TELEGRAM_API_ID,
    TELEGRAM_PARSER_SESSION_NAME,
)
from app.models import NewsItem
from app.news_parser.sources.rss_common import build_news_id


def _normalize_channel_username(value: str) -> str:
    return value.strip().lstrip("@").lower()


def _normalize_datetime(value: datetime | None) -> datetime:
    if value is None:
        return datetime.now(tz=timezone.utc)

    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)

    return value.astimezone(timezone.utc)


def _extract_message_text(message: Message) -> str:
    candidates = [
        getattr(message, "raw_text", None),
        getattr(message, "message", None),
        getattr(message, "text", None),
    ]

    for candidate in candidates:
        if candidate and candidate.strip():
            return candidate.strip()

    return ""


def _build_title_and_summary(text: str) -> tuple[str, str]:
    normalized = " ".join(text.split())

    if not normalized:
        return "", ""

    lines = [line.strip() for line in text.splitlines() if line.strip()]
    title = lines[0] if lines else normalized
    title = title[:160]

    summary = normalized[:500]
    return title, summary


@dataclass(frozen=True)
class TelegramChannelParser:
    """
    Парсер Telegram-канала через Telethon.

    Возвращает список NewsItem.
    """
    channel_username: str

    async def parse(self, limit: int = 20) -> list[NewsItem]:
        if not TELEGRAM_API_ID:
            raise RuntimeError("TELEGRAM_API_ID is not configured")

        if not TELEGRAM_API_HASH:
            raise RuntimeError("TELEGRAM_API_HASH is not configured")

        normalized_channel = _normalize_channel_username(self.channel_username)
        source_key = f"tg:{normalized_channel}"

        client = TelegramClient(
            session=f"{TELEGRAM_PARSER_SESSION_NAME}_{normalized_channel}",
            api_id=int(TELEGRAM_API_ID),
            api_hash=TELEGRAM_API_HASH,
        )

        items: list[NewsItem] = []

        async with client:
            entity = await client.get_entity(normalized_channel)

            async for message in client.iter_messages(entity, limit=limit):
                item = self._message_to_news_item(
                    message,
                    normalized_channel,
                    source_key,
                )
                if item:
                    items.append(item)

        items.reverse()
        return items

    def _message_to_news_item(
            self,
            message: Message,
            normalized_channel: str,
            source_key: str,
    ) -> NewsItem | None:
        if not getattr(message, "id", None):
            return None

        text = _extract_message_text(message)
        if not text:
            return None

        title, summary = _build_title_and_summary(text)
        if not title:
            return None

        published_at = _normalize_datetime(message.date)
        message_url = f"https://t.me/{normalized_channel}/{message.id}"

        news_id = build_news_id(
            source=source_key,
            title=title,
            url=message_url,
            published_at=published_at,
            raw_text=text,
        )

        return NewsItem(
            id=news_id,
            title=title,
            url=message_url,
            summary=summary,
            source=source_key,
            published_at=published_at,
            raw_text=text,
        )
