from __future__ import annotations

from datetime import datetime
from typing import Optional
from uuid import UUID, uuid4

from pydantic import BaseModel, Field


class NewsItem(BaseModel):
    id: UUID = Field(default_factory=uuid4)
    title: str
    url: Optional[str] = None
    summary: str
    source: str
    published_at: datetime
    raw_text: Optional[str] = None
