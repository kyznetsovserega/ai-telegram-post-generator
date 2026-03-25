from __future__ import annotations

from pathlib import Path
from typing import List

from app.models import LogItem
from app.config import APP_REDIS_URL
import redis


# --- JSONL storage (fallback) ---
class JsonlLogStorage:
    def __init__(self, path: Path = Path("data/logs.jsonl")) -> None:
        self.path = path
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def save(self, item: LogItem) -> None:
        with self.path.open("a", encoding="utf-8") as f:
            f.write(item.model_dump_json() + "\n")

    def list_all(self) -> List[LogItem]:
        if not self.path.exists():
            return []

        items = []
        with self.path.open("r", encoding="utf-8") as f:
            for line in f:
                items.append(LogItem.model_validate_json(line))
        return items


# --- Redis storage ---
class RedisLogStorage:
    KEY = "logs"

    def __init__(self) -> None:
        self.client = redis.from_url(APP_REDIS_URL, decode_responses=True)

    def save(self, item: LogItem) -> None:
        self.client.lpush(self.KEY, item.model_dump_json())

    def list_all(self) -> List[LogItem]:
        raw_items = self.client.lrange(self.KEY, 0, -1)
        return [LogItem.model_validate_json(item) for item in raw_items]
