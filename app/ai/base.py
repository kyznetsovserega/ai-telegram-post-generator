from __future__ import annotations

from typing import  Protocol

class TextGenerationClient(Protocol):
    async def generate_text(self,*,instructions: str,user_input:str) -> str:
        ...