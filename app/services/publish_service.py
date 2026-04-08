from __future__ import annotations

from app.models import LogItem, LogLevel, PostItem, PostStatus, utc_now
from app.services.log_service import LogService


class PublishService:
    """
    Сервис публикации Telegram-постов.

    Отвечает за:
    - получение publishable постов;
    - публикацию одного поста по id;
    - обновление статусов (PUBLISHED / FAILED);
    - сбор статистики;
    - логирование.
    """

    def __init__(
            self,
            post_storage,
            publisher,
            log_service: LogService,
    ):
        self.post_storage = post_storage
        self.publisher = publisher
        self.log_service = log_service

    def list_publishable_posts(self) -> list[PostItem]:
        """
        Возвращает все посты, готовые к публикации.
        """
        return self.post_storage.list_publishable()

    def publish_one_post(self, post_id: str) -> dict:
        """
        Публикует один конкретный пост по id.

        Возвращает словарь результата:
        - published: bool
        - skipped: bool
        - failed: bool
        - post_id
        - error (optional)
        """
        post = self.post_storage.get_by_id(post_id)

        if post is None:
            result = {
                "published": False,
                "skipped": False,
                "failed": True,
                "post_id": post_id,
                "error": "Post not found",
            }

            self.log_service.add_log(
                LogItem(
                    level=LogLevel.ERROR,
                    message="Publish skipped because post was not found",
                    source="publish_service",
                    context=result,
                )
            )
            return result

        # Повторно не публикуем
        if (
                post.status == PostStatus.PUBLISHED
                or post.external_message_id is not None
                or post.published_at is not None
        ):
            result = {
                "published": False,
                "skipped": True,
                "failed": False,
                "post_id": post.id,
                "reason": "already_published",
            }

            self.log_service.add_log(
                LogItem(
                    level=LogLevel.INFO,
                    message="Publish skipped because post is already published",
                    source="publish_service",
                    context={
                        "post_id": post.id,
                        "news_id": post.news_id,
                        "external_message_id": post.external_message_id,
                    },
                )
            )
            return result

        # Публикуем только GENERATED
        if post.status != PostStatus.GENERATED:
            result = {
                "published": False,
                "skipped": True,
                "failed": False,
                "post_id": post.id,
                "reason": f"invalid_status:{post.status.value}",
            }

            self.log_service.add_log(
                LogItem(
                    level=LogLevel.INFO,
                    message="Publish skipped because post status is not GENERATED",
                    source="publish_service",
                    context={
                        "post_id": post.id,
                        "news_id": post.news_id,
                        "status": post.status.value,
                    },
                )
            )
            return result

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
                self.post_storage.update(updated_post)

                response = {
                    "published": True,
                    "skipped": False,
                    "failed": False,
                    "post_id": post.id,
                    "external_message_id": result.external_id,
                }

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
                return response

            failed_post = post.model_copy(
                update={"status": PostStatus.FAILED}
            )
            self.post_storage.update(failed_post)

            response = {
                "published": False,
                "skipped": False,
                "failed": True,
                "post_id": post.id,
                "error": result.error_message or "Unknown publish failure",
            }

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
            return response

        except Exception as exc:
            failed_post = post.model_copy(
                update={"status": PostStatus.FAILED}
            )
            self.post_storage.update(failed_post)

            response = {
                "published": False,
                "skipped": False,
                "failed": True,
                "post_id": post.id,
                "error": str(exc),
            }

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
            return response
