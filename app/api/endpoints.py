from __future__ import annotations

from app.api.routers import router

# - файл оставлен, чтобы не ломать старые импорты,
#   но фактическая маршрутизация уже живёт в app.api.routers.
__all__ = ["router"]
