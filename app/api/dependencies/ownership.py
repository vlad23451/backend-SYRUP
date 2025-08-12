"""Зависимости проверки владения ресурсами.

Позволяют централизованно проверять принадлежность сущности текущему
пользователю и выбрасывать доменные исключения для единообразной обработки.
"""
from core.logger import app_logger
from database.managers.comment_manager import CommentManager
from database.managers.history_manager import HistoryManager
from database.managers.like_manager import (CommentDislikeManager,
                                            CommentLikeManager, DislikeManager,
                                            LikeManager)
from database.models.comment_like import CommentDislike, CommentLike
from database.models.comments import Comment
from database.models.history import History
from database.models.history_like import HistoryDislike, HistoryLike
from database.models.user import User
from exceptions.comment import OwnershipCommentError
from exceptions.histories import OwnershipHistoryError
from exceptions.like import (OwnershipCommentDislikeError,
                             OwnershipCommentLikeError, OwnershipDislikeError,
                             OwnershipLikeError)
from exceptions.users import UserNotFoundError

comment_manager = CommentManager()
history_manager = HistoryManager()
like_manager = LikeManager()
dislike_manager = DislikeManager()
comment_like_manager = CommentLikeManager()
comment_dislike_manager = CommentDislikeManager()

async def get_comment_or_error(id: int, user: User) -> Comment:
    comment = await comment_manager.get_obj_by_id(id=id)
    user_id = getattr(comment, 'user_id', None)
    if user_id is None:
        app_logger.error(f"Пользователь {user_id} не найден")
        raise UserNotFoundError()
    if user_id != user.id:
        app_logger.warning(f"Пользователь {user.id} попытался получить доступ к комментарию {id}")
        raise OwnershipCommentError()
    return comment

async def get_history_or_error(id: int, user: User) -> History:
    history = await history_manager.get_obj_by_id(id=id)
    author_id = getattr(history, 'author_id', None) 
    if author_id is None:
        app_logger.error(f"Пользователь {author_id} не найден")
        raise UserNotFoundError()
    if author_id != user.id:
        app_logger.warning(f"Пользователь {user.id} попытался получить доступ к истории {id}")
        raise OwnershipHistoryError()
    return history

async def get_like_or_error(id: int, user: User) -> HistoryLike:
    like = await like_manager.get_obj_by_id(id=id)
    user_id = getattr(like, 'user_id', None)
    if user_id is None:
        app_logger.error(f"Пользователь {user_id} не найден")
        raise UserNotFoundError()
    if user_id != user.id:
        app_logger.warning(f"Пользователь {user.id} попытался получить доступ к лайку {id}")
        raise OwnershipLikeError()
    return like

async def get_dislike_or_error(id: int, user: User) -> HistoryDislike:
    dislike = await dislike_manager.get_obj_by_id(id=id)
    user_id = getattr(dislike, 'user_id', None)
    if user_id is None:
        app_logger.error(f"Пользователь {user_id} не найден")
        raise UserNotFoundError()
    if user_id != user.id:
        app_logger.warning(f"Пользователь {user.id} попытался получить доступ к дизлайку {id}")
        raise OwnershipDislikeError()
    return dislike

async def get_comment_like_or_error(id: int, user: User) -> CommentLike:
    like = await comment_like_manager.get_obj_by_id(id=id)
    user_id = getattr(like, 'user_id', None)
    if user_id is None:
        app_logger.error(f"Пользователь {user_id} не найден")
        raise UserNotFoundError()
    if user_id != user.id:
        app_logger.warning(f"Пользователь {user.id} попытался получить доступ к лайку комментария {id}")
        raise OwnershipCommentLikeError()
    return like

async def get_comment_dislike_or_error(id: int, user: User) -> CommentDislike:
    dislike = await comment_dislike_manager.get_obj_by_id(id=id)
    user_id = getattr(dislike, 'user_id', None)
    if user_id is None:
        app_logger.error(f"Пользователь {user_id} не найден")
        raise UserNotFoundError()
    if user_id != user.id:
        app_logger.warning(f"Пользователь {user.id} попытался получить доступ к дизлайку комментария {id}")
        raise OwnershipCommentDislikeError()
    return dislike
