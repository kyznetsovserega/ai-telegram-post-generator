from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError

from app.api.endpoints import router as api_router


def create_app() -> FastAPI:
    # metadata приложения
    app = FastAPI(
        title="AI Telegram Post Generator",
        description="API для генерации и публикации Telegram-постов",
        version="1.0.0",
    )

    @app.get("/health")
    def health():
        return {"status": "ok"}

    # --- GLOBAL ERROR HANDLERS ---

    @app.exception_handler(Exception)
    async def global_exception_handler(request: Request, exc: Exception):
        # универсальный fallback
        return JSONResponse(
            status_code=500,
            content={
                "error": {
                    "type": type(exc).__name__,
                    "message": str(exc),
                }
            },
        )

    # обработка валидации (Pydantic / FastAPI)
    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(request: Request, exc: RequestValidationError):
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
