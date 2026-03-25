from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api.endpoints import router as api_router


def create_app() -> FastAPI:
    # приложение собираем через фабрику
    app = FastAPI(
        title="AI Telegram Post Generator",
        description="API для генерации и публикации Telegram-постов",
        version="1.0.0",
    )

    @app.get("/health")
    def health() -> dict[str, str]:
        """Простейший эндпоинт для проверки сервиса."""
        return {"status": "ok"}


    @app.exception_handler(StarletteHTTPException)
    async def http_exception_handler(
        request: Request,
        exc: StarletteHTTPException
    ) -> JSONResponse:
        # локальные HTTPException из API приводим к единому error payload
        if isinstance(exc.detail, dict) and "type" in exc.detail and "message" in exc.detail:
            error_payload = exc.detail
        else:
            error_payload = {
                "type": "HTTPException",
                "message": str(exc.detail),
            }

        return JSONResponse(
            status_code=exc.status_code,
            content={"error": error_payload},
        )


    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request,
        exc: RequestValidationError,
    ) -> JSONResponse:
        # ошибки входной валидации тоже держим в одном контракте ответа
        return JSONResponse(
            status_code=422,
            content={
                "error": {
                    "type": "ValidationError",
                    "message": "Invalid request data",
                    "details": exc.errors(),
                }
            },
        )

    # --- ROUTERS ---
    app.include_router(api_router, prefix="/api")
    return app


app = create_app()
