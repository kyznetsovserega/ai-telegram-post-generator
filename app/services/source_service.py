from __future__ import annotations

import re
from collections.abc import Callable
from urllib.parse import urlparse

from app.models import SourceItem, SourceType

AvailableSourceItemsProvider = Callable[[], list[SourceItem]]


class SourceService:
    """
    Сервис управления источниками.

    Отвечает за:
    - объединение catalog + storage;
    - CRUD пользовательских источников;
    - валидацию URL;
    - нормализацию id.
    """

    def __init__(self, storage, available_source_items_provider):
        self.storage = storage
        self.available_source_items_provider = available_source_items_provider

    def list_all(self) -> list[SourceItem]:
        """
        Возвращает список источников:
        - синхронизирует catalog → storage
        - возвращает итоговый список
        """
        catalog_sources = self.available_source_items_provider()
        self.storage.save_many(catalog_sources)
        return self.storage.list_all()

    def set_enabled(self, source_id: str, enabled: bool) -> SourceItem:
        """Изменяем состояние источника."""
        sources = self.list_all()

        target = next((source for source in sources if source.id == source_id), None)
        if target is None:
            raise LookupError(f"Source not found: {source_id}")

        target.enabled = enabled
        self.storage.write_all(sources)
        return target

    def create_source(
            self,
            *,
            source_type: SourceType,
            name: str,
            url: str | None = None,
            enabled: bool = True,
            source_id: str | None = None,
    ) -> SourceItem:
        """
        Создание пользовательского источника.
        """
        normalized_name = name.strip()
        if not normalized_name:
            raise ValueError("Source name must not be empty")

        normalized_url = self._normalize_optional_url(url)

        if source_type == SourceType.SITE:
            validated_url = self._validate_site_url(normalized_url)
            normalized_id = self._build_site_id(source_id, normalized_name)
            item = SourceItem(
                id=normalized_id,
                type=SourceType.SITE,
                name=normalized_name,
                url=validated_url,
                enabled=enabled,
            )
        else:
            normalized_id = self._build_tg_id(source_id, normalized_name, normalized_url)
            item = SourceItem(
                id=normalized_id,
                type=SourceType.TG,
                name=normalized_name,
                url=normalized_url,
                enabled=enabled,
            )

        existing = self.storage.get_by_id(item.id)
        if existing is not None:
            raise ValueError(f"Source already exists: {item.id}")

        self.storage.save_many([item])
        return item

    def delete_source(self, source_id: str) -> None:
        """
        Удаление пользовательского источника.
        """
        catalog_ids = {item.id for item in self.available_source_items_provider()}

        if source_id in catalog_ids:
            raise ValueError(f"Built-in catalog source cannot be deleted: {source_id}")

        sources = self.storage.list_all()
        filtered_sources = [source for source in sources if source.id != source_id]

        if len(filtered_sources) == len(sources):
            raise LookupError(f"Source not found: {source_id}")

        self.storage.write_all(filtered_sources)

    def update_source(
            self,
            source_id: str,
            name: str | None = None,
            url: str | None = None,
            enabled: bool | None = None,
    ) -> SourceItem:
        """
        Частичное обновление источника.
        """
        sources = self.list_all()

        target = next((source for source in sources if source.id == source_id), None)
        if target is None:
            raise LookupError(f"Source not found: {source_id}")

        if name is not None:
            normalized_name = name.strip()
            if not normalized_name:
                raise ValueError("Source name must not be empty")
            target.name = normalized_name

        if url is not None:
            normalized_url = self._normalize_optional_url(url)

            if target.type == SourceType.SITE:
                target.url = self._validate_site_url(normalized_url)
            else:
                target.url = normalized_url

        if enabled is not None:
            target.enabled = enabled

        self.storage.write_all(sources)
        return target

    @staticmethod
    def _normalize_optional_url(value: str | None) -> str | None:
        if value is None:
            return None

        normalized = value.strip()
        return normalized or None

    @staticmethod
    def _slugify(value: str) -> str:
        slug = value.strip().lower()
        slug = re.sub(r"^https?://", "", slug)
        slug = slug.replace("t.me/", "")
        slug = slug.replace("@", "")
        slug = re.sub(r"[^a-z0-9]+", "-", slug)
        slug = slug.strip("-")

        if not slug:
            raise ValueError("Could not generate a valid source id")

        return slug

    def _build_site_id(self, source_id: str | None, name: str) -> str:
        """ Для site не используем префикс site. """
        raw = source_id.strip() if source_id else name
        normalized_id = self._slugify(raw)

        if normalized_id.startswith("tg-") or normalized_id.startswith("tg:"):
            raise ValueError("Site source id must not use Telegram prefix")

        return normalized_id

    def _build_tg_id(self, source_id: str | None, name: str, url: str | None) -> str:
        """
        Для tg всегда храним id в формате tg:<slug>.
        """
        raw = source_id or url or name
        raw = raw.strip()

        if raw.startswith("tg:"):
            raw = raw[3:]

        normalized_slug = self._slugify(raw)
        return f"tg:{normalized_slug}"

    @staticmethod
    def _validate_site_url(url: str | None) -> str:
        if url is None:
            raise ValueError("Site source url is required")

        parsed = urlparse(url)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("Site source url must be a valid http/https URL")

        return url
