from __future__ import annotations

from app.models import PostItem, PostStatus
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
        Публикуем только посты со статусом GENERATED.
        Возвращает краткую статистику по шагу publish.
        """
        posts = self.post_storage.list_all()
        generated_posts = [post for post in posts if post.status == PostStatus.GENERATED]

        if not generated_posts:
            return {
                "total": 0,
                "published": 0,
                "skipped": 0,
                "failed": 0,
            }

        updated_posts: list[PostItem] = []
        published_ids: set[str] = set()
        failed_ids: set[str] = set()

        for post in generated_posts:
            try:
                result = self.publisher.publish_post(post.generated_text)

                if result.is_published:
                    updated_posts.append(
                        post.model_copy(
                            update={
                                "status": PostStatus.PUBLISHED,
                            }
                        )
                    )
                    published_ids.add(post.id)
                else:
                    updated_posts.append(
                        post.model_copy(update={"status": PostStatus.FAILED})
                    )
                    failed_ids.add(post.id)

            except Exception:
                updated_posts.append(
                    post.model_copy(update={"status": PostStatus.FAILED})
                )
                failed_ids.add(post.id)

        updated_by_id = {post.id: post for post in updated_posts}

        final_posts = [
            updated_by_id.get(post.id, post)
            for post in posts
        ]

        self.post_storage.write_all(final_posts)

        return {
            "total": len(generated_posts),
            "published": len(published_ids),
            "skipped": 0,
            "failed": len(failed_ids),
        }
