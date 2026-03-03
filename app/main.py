from fastapi import FastAPI

from app.api.endpoints import router as api_router

app = FastAPI(
    title="AI Telegram Post Generator",
    description="Api для управления AI-генерацией постов и источников",
    version="0.1.0",
)

app.include_router(api_router, prefix="/api")


@app.get("/health")
async def health_check():
    """Простейший эндпоинт для проверки сервиса."""
    return {"status": "ok"}
