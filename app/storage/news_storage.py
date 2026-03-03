from __future__ import annotations

import json
from pathlib import Path
from typing import Iterable

from app.models import NewsItem


class JsonNewsStorage:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def append_many(self, items: Iterable[NewsItem]) -> int:
        count = 0
        with self.path.open("a", encoding="utf-8") as f:
            for item in items:
                f.write(item.model_dump_json())
                f.write("\n")
                count += 1
        return count
