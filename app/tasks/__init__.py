from app.tasks.cleanup import cleanup_indexes
from app.tasks.collect import collect_sites_task, ping
from app.tasks.filter import filter_news_task
from app.tasks.generate import generate_posts_task
from app.tasks.pipeline import (
    pipeline_chain_task,
    collect_filter_generate_posts_task,
)
from app.tasks.publish import publish_posts_task

__all__ = [
    "ping",
    "collect_sites_task",
    "filter_news_task",
    "generate_posts_task",
    "publish_posts_task",
    "pipeline_chain_task",
    "collect_filter_generate_posts_task",
    "cleanup_indexes",
]
