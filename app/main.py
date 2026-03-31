from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routers import router as api_router
from app.config import APP_REDIS_URL, LLM_PROVIDER, STORAGE_BACKEND


def create_app() -> FastAPI:
    """
    Фабрика FastAPI-приложения.

    - метаданные приложения
    - подключение общих handlers
    - регистрацию роутеров
    - системные маршруты
    """
    app = FastAPI(
        title="AI Telegram Post Generator",
        description="API для генерации и публикации Telegram-постов",
        version="1.0.0",
    )
    register_exception_handlers(app)

    @app.get("/health", tags=["system"])
    def health() -> dict[str, str | bool]:
        """
        Информативный health endpoint.

        - status
        - storage_backend
        - llm_provider
        - redis_configured
        """
        return {
            "status": "ok",
            # текущий storage backend из config.py
            "storage_backend": STORAGE_BACKEND,
            # текущего AI-провайдера из config.py
            "llm_provider": LLM_PROVIDER,
            # признак настройки Redis, без вывода самого URL
            "redis_configured": bool(APP_REDIS_URL.strip()),
        }


    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
