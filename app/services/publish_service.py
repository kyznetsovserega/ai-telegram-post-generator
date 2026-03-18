from __future__ import annotations

from app.models import PostItem, PostStatus, utc_now
from app.storage.posts import JsonlPostStorage
from app.telegram.publisher import TelegramPublisher


class PublishService:
    """Сервис публикации сгенерированных постов."""

    def __init__(
            self,
            post_storage: JsonlPostStorage | None = None,
            publisher: TelegramPublisher | None = None,
    ) -> None:
        self.post_storage = post_storage or JsonlPostStorage()
        self.publisher = publisher or TelegramPublisher()

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
