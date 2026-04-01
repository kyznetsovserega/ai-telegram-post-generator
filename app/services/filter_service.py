from __future__ import annotations

from app.models import NewsItem, NewsStatus, KeywordType, LogItem, LogLevel
from app.services.filters import (
    DedupFilter,
    FilterContext,
    KeywordFilter,
    LanguageFilter,
    SourceFilter,
)
from app.services.keyword_service import KeywordService
from app.storage.news import generate_content_hash


class FilterService:
    """
    Оркестратор фильтрации новостей.

    - получает include / exclude keywords
    - получает enabled sources
    - подготавливает searchable_text и content_hash
    - прогоняет news item через цепочку filter rules
    - возвращает filtered_items и dropped_items
    - логирует причину drop
    """

    def __init__(
            self,
            keyword_service: KeywordService,
            log_service,
            source_service=None,
    ) -> None:
        self.keyword_service = keyword_service
        self.log_service = log_service
        self.source_service = source_service

        # Порядок применения правил:
        # 1) source
        # 2) language
        # 3) dedup
        # 4) keywords
        self.rules = [
            SourceFilter(),
            LanguageFilter(),
            DedupFilter(),
            KeywordFilter(),
        ]

    def apply_filter(
            self,
            items: list[NewsItem],
    ) -> tuple[list[NewsItem], list[NewsItem]]:
        include_keywords = [
            item.value
            for item in self.keyword_service.list_by_type(KeywordType.INCLUDE)
        ]
        exclude_keywords = [
            item.value
            for item in self.keyword_service.list_by_type(KeywordType.EXCLUDE)
        ]
        enabled_source_ids = self._get_enabled_source_ids()

        filtered_items: list[NewsItem] = []
        dropped_items: list[NewsItem] = []

        seen_ids: set[str] = set()
        seen_hashes: set[str] = set()

        for item in items:
            prepared_item = self._prepare_item(item)
            searchable_text = self._build_searchable_text(prepared_item)

            context = FilterContext(
                searchable_text=searchable_text,
                include_keywords=include_keywords,
                exclude_keywords=exclude_keywords,
                enabled_source_ids=enabled_source_ids,
                seen_ids=seen_ids,
                seen_hashes=seen_hashes,
            )

            failed_reason = self._get_failed_reason(prepared_item, context)
            if failed_reason is not None:
                dropped_item = prepared_item.model_copy(
                    update={"status": NewsStatus.DROPPED}
                )
                self._log_drop(dropped_item, failed_reason)
                dropped_items.append(dropped_item)
                continue

            filtered_items.append(
                prepared_item.model_copy(update={"status": NewsStatus.FILTERED})
            )

        return filtered_items, dropped_items

    def _prepare_item(self, item: NewsItem) -> NewsItem:
        """
        Подготовка item перед запуском правил.
        Content_hash считаем один раз в начале.
        """
        content_hash = generate_content_hash(item)
        return item.model_copy(update={"content_hash": content_hash})

    def _get_failed_reason(
            self,
            item: NewsItem,
            context: FilterContext,
    ) -> str | None:
        """
        Прогоняем item по всем правилам.
        На первом reject возвращаем reason.
        """
        for rule in self.rules:
            result = rule.apply(item, context)
            if not result.passed:
                return result.reason
        return None

    def _get_enabled_source_ids(self) -> set[str] | None:
        """
        Получаем enabled source ids из SourceService.

        Если source_service не передан,
        source filtering отключается.
        """
        if self.source_service is None:
            return None

        return {
            source.id
            for source in self.source_service.list_all()
            if source.enabled
        }

    def _log_drop(self, item: NewsItem, reason: str) -> None:
        self.log_service.add_log(
            LogItem(
                level=LogLevel.INFO,
                message="News item dropped",
                source="filter",
                context={
                    "reason": reason,
                    "news_id": item.id,
                    "source": item.source,
                },
            )
        )

    def _build_searchable_text(self, item: NewsItem) -> str:
        parts = [
            item.title.strip(),
            item.summary.strip(),
            (item.raw_text or "").strip(),
        ]
        return " ".join(part for part in parts if part).lower()
