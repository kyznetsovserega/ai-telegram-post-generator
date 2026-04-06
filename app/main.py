from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi

from app.api.errors import get_default_responses, register_exception_handlers
from app.api.routers import router as api_router
from app.api.schemas import HealthResponse
from app.config import APP_REDIS_URL, LLM_PROVIDER, STORAGE_BACKEND


def custom_openapi(app: FastAPI) -> dict:
    if app.openapi_schema:
        return app.openapi_schema

    openapi_schema = get_openapi(
        title=app.title,
        version=app.version,
        description=app.description,
        routes=app.routes,
    )

    # Убираем стандартные схемы валидации FastAPI,
    # чтобы в Swagger остался только наш единый ErrorResponse.
    for path_item in openapi_schema.get("paths", {}).values():
        for operation in path_item.values():
            if not isinstance(operation, dict):
                continue

            responses = operation.get("responses", {})
            responses.pop("422", None)

    components = openapi_schema.get("components", {})
    schemas = components.get("schemas", {})
    schemas.pop("HTTPValidationError", None)
    schemas.pop("ValidationError", None)

    app.openapi_schema = openapi_schema
    return app.openapi_schema


def create_app() -> FastAPI:
    app = FastAPI(
        title="AI Telegram Post Generator",
        description="""
AI Telegram Post Generator API

Система автоматической генерации и публикации Telegram-постов.

Pipeline:
collect → filter → generate → publish

Возможности:
- сбор новостей (sites + telegram)
- фильтрация по ключевым словам
- генерация постов через LLM
- публикация в Telegram
- управление источниками и фильтрами
- просмотр логов и истории

Storage: Redis / JSONL
LLM: OpenAI / Gemini / Free LLM
Background: Celery + Redis
""",
        version="1.0.0",
        contact={
            "name": "AI Telegram Post Generator",
        },
        openapi_tags=[
            {
                "name": "System",
                "description": "System endpoints (health, service info)",
            },
            {
                "name": "Collect",
                "description": "News collection from sites and Telegram",
            },
            {
                "name": "Generate",
                "description": "LLM-based post generation",
            },
            {
                "name": "Sources",
                "description": "Manage news sources",
            },
            {
                "name": "Keywords",
                "description": "Manage filtering keywords",
            },
            {
                "name": "Posts",
                "description": "Generated posts history",
            },
            {
                "name": "Logs",
                "description": "System logs",
            },
            {
                "name": "News",
                "description": "Collected news",
            },
        ],
    )

    register_exception_handlers(app)

    @app.get(
        "/health",
        tags=["System"],
        summary="Health check",
        description="Returns system status and configuration info.",
        response_model=HealthResponse,
        responses={
            200: {"description": "Service is healthy"},
            **get_default_responses(),
        },
    )
    def health() -> HealthResponse:
        return HealthResponse(
            status="ok",
            storage_backend=STORAGE_BACKEND,
            llm_provider=LLM_PROVIDER,
            redis_configured=bool(APP_REDIS_URL.strip()),
        )

    app.include_router(api_router, prefix="/api")
    app.openapi = lambda: custom_openapi(app)

    return app


app = create_app()
