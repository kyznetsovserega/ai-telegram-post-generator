from fastapi import FastAPI

from app.api.endpoints import router as api_router

app = FastAPI()

@app.get("/health")
def health():
    """Простейший эндпоинт для проверки сервиса."""
    return {"status": "ok"}

app.include_router(api_router, prefix="/api")
