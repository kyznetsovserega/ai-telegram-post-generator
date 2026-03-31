from fastapi import FastAPI

from app.api.errors import register_exception_handlers
from app.api.routers import router as api_router


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
    def health() -> dict[str, str]:
        """Простейший эндпоинт для проверки сервиса."""
        return {"status": "ok"}


    app.include_router(api_router, prefix="/api")

    return app


app = create_app()
