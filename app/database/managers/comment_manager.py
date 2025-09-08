from __future__ import annotations

import asyncio
from typing import Dict
from typing import List

from core.logger import app_logger

from database.managers.base_manager import BaseManager
from database.managers.history_manager import HistoryManager
from database.managers.session_manager import Manager
from database.managers.user_manager import UserManager

from database.models.comment_like import CommentDislike
from database.models.comment_like import CommentLike
from database.models.comments import Comment
from database.models.user import User

from exceptions.histories import HistoryNotFoundError

from schemas.comment import CommentOut, CommentUpdate
from schemas.user import UserShortOutWithFollowStatus

from services.cache_service import CommentsByHistoryCacheService
from services.user_builders_service import build_user_list
from services.user_builders_service import build_users_map
from services.user_info_service import build_user_info
from services.user_info_service import build_user_info_many

from sqlalchemy import func
from sqlalchemy import select

manager = Manager()
user_manager = UserManager()
history_manager = HistoryManager()

class CommentManager(BaseManager[Comment, CommentUpdate]):
    def __init__(self):
        super().__init__(Comment)

    @staticmethod
    def _select_comments_by_history(history_id: int):
        return (
            select(Comment)
            .filter_by(history_id=history_id)
            .order_by(Comment.created_at.desc())
        )

    @staticmethod
    def _select_count_for_comments(model, comment_ids: List[int]):
        return (
            select(model.comment_id, func.count(model.id).label('count'))
            .where(model.comment_id.in_(comment_ids))
            .group_by(model.comment_id)
        )

    @staticmethod
    def _select_users_for_comments(model, comment_ids: List[int]):
        return (
            select(model.comment_id, User)
            .join(User, model.user_id == User.id)
            .where(model.comment_id.in_(comment_ids))
        )

    @staticmethod
    def _select_users_for_single(model, comment_id: int):
        return (
            select(User)
            .join(model, model.user_id == User.id)
            .where(model.comment_id == comment_id)
        )

    @staticmethod
    def _select_count_for_single(model, comment_id: int):
        return select(func.count(model.id)).where(model.comment_id == comment_id)

    @staticmethod
    async def _get_like_dislike_maps(comment_ids: List[int]):
        async with manager.get_async_session() as session:
            likes_result = await session.execute(
                CommentManager._select_count_for_comments(CommentLike, comment_ids)
            )
            likes_map = {row.comment_id: row.count for row in likes_result}

            dislikes_result = await session.execute(
                CommentManager._select_count_for_comments(CommentDislike, comment_ids)
            )
            dislikes_map = {row.comment_id: row.count for row in dislikes_result}

        return likes_map, dislikes_map

    @staticmethod
    async def _get_user_maps(comment_ids: List[int],
                             me_user_id: int) -> tuple[Dict[int, List[UserShortOutWithFollowStatus]]]:
        async with manager.get_async_session() as session:
            liked_rows = await session.execute(
                CommentManager._select_users_for_comments(CommentLike, comment_ids)
            )
            disliked_rows = await session.execute(
                CommentManager._select_users_for_comments(CommentDislike, comment_ids)
            )

        liked_users_map = await build_users_map(liked_rows, me_user_id)
        disliked_users_map = await build_users_map(disliked_rows, me_user_id)
        
        return liked_users_map, disliked_users_map

    @staticmethod
    async def _get_single_like_dislike_counts(comment_id: int):
        async with manager.get_async_session() as session:
            likes_result = await session.execute(
                CommentManager._select_count_for_single(CommentLike, comment_id))
            likes_count = likes_result.scalar() or 0

            dislikes_result = await session.execute(
                CommentManager._select_count_for_single(CommentDislike, comment_id))
            dislikes_count = dislikes_result.scalar() or 0

        return likes_count, dislikes_count

    @staticmethod
    async def _get_users_for_comment(comment_id: int, me_user_id: int) -> tuple[List[UserShortOutWithFollowStatus], List[UserShortOutWithFollowStatus]]:
        async with manager.get_async_session() as session:
            liked_rows = await session.execute(CommentManager._select_users_for_single(CommentLike,
                                                                                       comment_id))
            disliked_rows = await session.execute(CommentManager._select_users_for_single(CommentDislike,
                                                                                          comment_id))

        liked_users = await build_user_list(liked_rows, me_user_id)
        disliked_users = await build_user_list(disliked_rows, me_user_id)

        return liked_users, disliked_users

    @staticmethod
    async def get_comments_by_history_id(id: int,
                                         user_id: int,
                                         skip: int = 0,
                                         limit: int = 10) -> List[CommentOut]:
        cached = await CommentsByHistoryCacheService.get_comments(history_id=id,
                                    skip=skip, limit=limit, me_user_id=user_id)
        if cached is not None:
            return cached

        history = await history_manager.get_history_by_id(id)
        if not history:
            raise HistoryNotFoundError()
        
        async with manager.get_async_session() as session:
            comments = await session.execute(
                CommentManager._select_comments_by_history(history.id).offset(skip).limit(limit)
            )
            comments = comments.scalars().all()

        comment_ids = [comment.id for comment in comments]
        likes_map_task = asyncio.create_task(CommentManager._get_like_dislike_maps(comment_ids))
        user_maps_task = asyncio.create_task(CommentManager._get_user_maps(comment_ids, me_user_id=user_id))
        likes_map, dislikes_map = await likes_map_task
        liked_users_map, disliked_users_map = await user_maps_task

        comment_outs = []

        author_ids = list({c.user_id for c in comments})
        # Параллельный сбор авторов
        authors = await asyncio.gather(*[user_manager.get_obj_by_id(uid) for uid in author_ids])
        author_info_map = await build_user_info_many(me_user_id=user_id, users=authors)

        for comment in comments:
            user_info = author_info_map.get(comment.user_id) or await build_user_info(me_user_id=user_id,
                                                  user=await user_manager.get_obj_by_id(comment.user_id))
                
            likes_count = likes_map.get(comment.id, 0)
            dislikes_count = dislikes_map.get(comment.id, 0)
            
            comment_out = CommentOut.from_model_with_counts(
                comment=comment,
                user_info=user_info,
                likes_count=likes_count,
                dislikes_count=dislikes_count,
                liked_users=liked_users_map.get(comment.id, []),
                disliked_users=disliked_users_map.get(comment.id, []),
            )
            comment_outs.append(comment_out)

        await CommentsByHistoryCacheService.set_comments(history_id=id,
            skip=skip, limit=limit, me_user_id=user_id, data=comment_outs)
        return comment_outs
