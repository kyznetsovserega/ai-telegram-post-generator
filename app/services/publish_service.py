from __future__ import annotations

from app.models import LogItem, LogLevel, PostStatus, utc_now
from app.services.log_service import LogService


class PublishService:
    """Сервис публикации сгенерированных постов."""

    def __init__(
            self,
            post_storage,
            publisher,
            log_service: LogService,
    ):
        self.post_storage = post_storage
        self.publisher = publisher
        self.log_service = log_service

    def publish_generated_posts(self) -> dict:
        """
        Публикуем только еще не опубликованные посты.
        """
        publishable_posts = self.post_storage.list_publishable()
        total_posts = len(self.post_storage.list_all())

        if not publishable_posts:
            return {
                "total": 0,
                "published": 0,
                "skipped": total_posts,
                "failed": 0,
                "published_post_ids": [],
                "failed_post_ids": [],
                "errors": [],
            }

        published_ids: list[str] = []
        failed_ids: list[str] = []
        errors: list[dict[str, str]] = []

        for post in publishable_posts:
            try:
                result = self.publisher.publish_post(post.generated_text)

                if result.is_published:
                    updated_post = post.model_copy(
                        update={
                            "status": PostStatus.PUBLISHED,
                            "published_at": utc_now(),
                            "external_message_id": result.external_id,
                        }
                    )

                    # точечно обновляем только этот пост
                    self.post_storage.update(updated_post)
                    published_ids.append(post.id)

                    self.log_service.add_log(
                        LogItem(
                            level=LogLevel.INFO,
                            message="Post published successfully",
                            source="publish_service",
                            context={
                                "post_id": post.id,
                                "news_id": post.news_id,
                                "external_message_id": result.external_id,
                            },
                        )
                    )
                else:
                    failed_post = post.model_copy(
                        update={"status": PostStatus.FAILED}
                    )

                    # точечно обновляем только этот пост
                    self.post_storage.update(failed_post)
                    failed_ids.append(post.id)
                    errors.append(
                        {
                            "post_id": post.id,
                            "reason": result.error_message or "Unknown publish failure",
                        }
                    )

                    self.log_service.add_log(
                        LogItem(
                            level=LogLevel.ERROR,
                            message="Post publish failed",
                            source="publish_service",
                            context={
                                "post_id": post.id,
                                "news_id": post.news_id,
                                "reason": result.error_message,
                            },
                        )
                    )

            except Exception as exc:
                failed_post = post.model_copy(
                    update={"status": PostStatus.FAILED}
                )

                # при exception фиксируем failed точечно
                self.post_storage.update(failed_post)
                failed_ids.append(post.id)
                errors.append(
                    {
                        "post_id": post.id,
                        "reason": str(exc),
                    }
                )

                self.log_service.add_log(
                    LogItem(
                        level=LogLevel.ERROR,
                        message="Post publish raised exception",
                        source="publish_service",
                        context={
                            "post_id": post.id,
                            "news_id": post.news_id,
                            "reason": str(exc),
                            "exception_type": type(exc).__name__,
                        },
                    )
                )

        return {
            "total": len(publishable_posts),
            "published": len(published_ids),
            "skipped": total_posts - len(publishable_posts),
            "failed": len(failed_ids),
            "published_post_ids": published_ids,
            "failed_post_ids": failed_ids,
            "errors": errors,
        }
