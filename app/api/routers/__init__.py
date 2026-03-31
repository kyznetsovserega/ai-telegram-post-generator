from fastapi import APIRouter

from app.api.routers.sources import router as sources_router
from app.api.routers.keywords import router as keywords_router
from app.api.routers.generate import router as generate_router
from app.api.routers.collect import router as collect_router
from app.api.routers.posts import router as posts_router
from app.api.routers.logs import router as logs_router
from .news import router as news_router

router = APIRouter()

router.include_router(sources_router, tags=["Sources"])
router.include_router(keywords_router, tags=["Keywords"])
router.include_router(generate_router, tags=["Generate"])
router.include_router(collect_router, tags=["Collect"])
router.include_router(posts_router, tags=["Posts"])
router.include_router(logs_router, tags=["Logs"])
router.include_router(news_router,tags=["News"])
