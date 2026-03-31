from __future__ import annotations

from dataclasses import dataclass, field

from app.models import NewsItem


@dataclass(slots=True)
class FilterContext:
    """
    Общий контекст фильтрации одной новости.

    searchable_text:
        Нормализованный текст, по которому работают keyword/language filters.

    include_keywords / exclude_keywords:
        Актуальные правила из KeywordService.

    enabled_source_ids:
        Список разрешённых источников.
        Если None -> source filter считается отключённым.

    seen_ids / seen_hashes:
        In-memory дедупликация внутри текущего батча.
    """

    searchable_text: str
    include_keywords: list[str]
    exclude_keywords: list[str]
    enabled_source_ids: set[str] | None = None
    seen_ids: set[str] = field(default_factory=set)
    seen_hashes: set[str] = field(default_factory=set)


@dataclass(slots=True)
class FilterResult:
    """Результат применения одного фильтра."""

    passed: bool
    reason: str | None = None

    @classmethod
    def ok(cls) -> "FilterResult":
        return cls(passed=True, reason=None)

    @classmethod
    def reject(cls, reason: str) -> "FilterResult":
        return cls(passed=False, reason=reason)


class FilterRule:
    """Базовый контракт для любого фильтра."""

    def apply(self, item: NewsItem, context: FilterContext) -> FilterResult:
        raise NotImplementedError
