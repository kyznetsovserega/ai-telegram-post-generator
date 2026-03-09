from __future__ import annotations

from typing import List

from pydantic import BaseModel, Field


# --- Collect ---

class CollectSitesRequest(BaseModel):
    sites: List[str] = Field(default_factory=lambda: ["habr"])
    limit_per_site: int = Field(default=20, ge=1 , le=100)


class CollectSitesResponse(BaseModel):
    requested_sites: List[str]
    collected: int
    saved: int

# --- Generate ---

class GenerateRequest(BaseModel):
    """ Ручной ввод текста и генерация поста. """
    text: str = Field(min_length=1, max_length=500)

class GenerateResponse(BaseModel):
    generated_text: str