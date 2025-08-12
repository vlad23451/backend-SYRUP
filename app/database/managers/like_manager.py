from typing import Generic, Type, TypeVar

from database.models.comment_like import CommentDislike, CommentLike
from database.models.history_like import HistoryDislike, HistoryLike
from exceptions.base import DatabaseError
from sqlalchemy import delete, select

from .base_manager import BaseManager

T = TypeVar('T')

class BaseReactionManager(BaseManager[T, object], Generic[T]):
    def __init__(self, model: Type[T], target_field: str):
        super().__init__(model)
        self._target_field = target_field

    def _stmt_by_user_and_target(self, user_id: int, target_id: int):
        return (getattr(self._model, "user_id") == user_id,
            getattr(self._model, self._target_field) == target_id,)

    async def get_by_user_and_target(self, user_id: int, target_id: int) -> T | None:
        async with self.manager.get_async_session() as session:
            result = await session.execute(
                select(self._model).where(*self._stmt_by_user_and_target(user_id, target_id)))
            return result.scalars().first()

    async def delete_by_user_and_target(self, user_id: int, target_id: int) -> None:
        async with self.manager.get_async_session() as session:
            try:
                await session.execute(
                    delete(self._model).where(*self._stmt_by_user_and_target(user_id, target_id)))
                await session.commit()
            except Exception:
                await session.rollback()
                raise DatabaseError()


class LikeManager(BaseReactionManager[HistoryLike]):
    def __init__(self):
        super().__init__(HistoryLike, "history_id")


class DislikeManager(BaseReactionManager[HistoryDislike]):
    def __init__(self):
        super().__init__(HistoryDislike, "history_id")


class CommentLikeManager(BaseReactionManager[CommentLike]):
    def __init__(self):
        super().__init__(CommentLike, "comment_id")


class CommentDislikeManager(BaseReactionManager[CommentDislike]):
    def __init__(self):
        super().__init__(CommentDislike, "comment_id")
