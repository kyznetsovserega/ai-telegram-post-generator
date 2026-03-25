from __future__ import annotations

from app.models import LogItem, LogLevel, PostItem, PostStatus, utc_now
from app.services.log_service import LogService
from app.storage import get_post_storage
from app.telegram.publisher import TelegramPublisher


class PublishService:
    """Сервис публикации сгенерированных постов."""

    def __init__(
            self,
            publisher: TelegramPublisher | None = None,
    ) -> None:
        self.post_storage = get_post_storage()
        self.publisher = publisher or TelegramPublisher()
        self.log_service = LogService()

    def publish_generated_posts(self) -> dict:
        """
        Публикуем только еще не опубликованные посты.
        """
        all_posts = self.post_storage.list_all()
        publishable_posts = self.post_storage.list_publishable()

        if not publishable_posts:
            return {
                "total": 0,
                "published": 0,
                "skipped": 0,
                "failed": 0,
                "published_post_ids": [],
                "failed_post_ids": [],
                "errors": [],
            }

        updated_posts: list[PostItem] = []
        published_ids: list[str] = []
        failed_ids: list[str] = []
        errors: list[dict[str, str]] = []

        for post in publishable_posts:
            try:
                result = self.publisher.publish_post(post.generated_text)

                if result.is_published:
                    updated_posts.append(
                        post.model_copy(
                            update={
                                "status": PostStatus.PUBLISHED,
                                "published_at": utc_now(),
                                "external_message_id": result.external_id,
                            }
                        )
                    )
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
                    updated_posts.append(
                        post.model_copy(update={"status": PostStatus.FAILED})
                    )
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
                updated_posts.append(
                    post.model_copy(update={"status": PostStatus.FAILED})
                )
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
                            "reason": str,
                            "exception_type":type(exc).__name__,
                        },
                    )
                )

        updated_by_id = {post.id: post for post in updated_posts}

        final_posts = [
            updated_by_id.get(post.id, post)
            for post in all_posts
        ]

        self.post_storage.write_all(final_posts)

        return {
            "total": len(publishable_posts),
            "published": len(published_ids),
            "skipped": 0,
            "failed": len(failed_ids),
            "published_post_ids": published_ids,
            "failed_post_ids": failed_ids,
            "errors": errors,
        }
