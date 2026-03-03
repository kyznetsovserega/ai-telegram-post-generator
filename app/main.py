from fastapi import FastAPI

app = FastAPI(
    title="AI Telegram Post Generator",
    description="Api для управления AI-генерацией постов и источников",
    version="0.1.0",
)


@app.get("/health")
async def health_check():
    """Простейший эндпоинт для проверки сервиса."""
    return {"status": "ok"}
