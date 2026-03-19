from __future__ import annotations

from app.models import SourceItem
from app.news_parser.sites import available_source_items


class SourceService:
    """ Read-only сервис просмотра доступных источников. """

    def list_all(self) -> list[SourceItem]:
        return available_source_items()
