from __future__ import annotations

from typing import Dict
from typing import List
from typing import Optional
from typing import Tuple
from typing import TypeVar

from core.logger import app_logger

from database.managers.base_manager import BaseManager

from database.models.comments import Comment
from database.models.history import History
from database.models.history_like import HistoryDislike
from database.models.history_like import HistoryLike
from database.models.history_score import HistoryScore
from database.models.user import User

from exceptions.base import DatabaseError
from exceptions.histories import HistoryNotFoundError

from schemas.history import HistoryOut
from schemas.history import HistoryOutShort
from schemas.history import HistoryUpdate
from schemas.user import UserShortOutWithFollowStatus

from services.cache_service import (
    HistoriesByAuthorCacheService,
    FriendsHistoriesCacheService,
    FollowingHistoriesCacheService,
)
from services.cache_service import HistoryCacheService
from services.user_builders_service import build_user_list
from services.user_builders_service import build_users_map
from services.score_service import ScoreService

from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

T = TypeVar('T')

class HistoryManager(BaseManager[History, HistoryUpdate]):
    def __init__(self) -> None:
        super().__init__(History)

    # History and Author Query Builders - StaticMethods

    @staticmethod
    def _select_with_author():
        return select(History).options(joinedload(History.author))
    
    @staticmethod
    def _select_with_author_by_author_id(author_id: int):
        return HistoryManager._select_with_author().where(History.author_id == author_id)

    @staticmethod
    def _select_with_author_by_id(id: int):
        return HistoryManager._select_with_author().where(History.id == id)
    
    @staticmethod
    def _select_by_author_id(author_id: int):
        return select(History).where(History.author_id == author_id)
    
    # Like / Dislike Query Builders - StaticMethods

    @staticmethod
    def _select_like_count_map(model, history_ids: List[int]):
        return (
            select(model.history_id, func.count(model.id))
            .where(model.history_id.in_(history_ids))
            .group_by(model.history_id)
        )
    
    @staticmethod
    def _select_like_count_single(history_id: int):
        return select(func.count(HistoryLike.id)).where(HistoryLike.history_id == history_id)

    @staticmethod
    def _select_dislike_count_single(history_id: int):
        return select(func.count(HistoryDislike.id)).where(HistoryDislike.history_id == history_id)
    
    @staticmethod
    def _select_users_who_liked_histories(history_ids: List[int]):
        return (
            select(HistoryLike.history_id, User)
            .join(User, HistoryLike.user_id == User.id)
            .where(HistoryLike.history_id.in_(history_ids))
        )

    @staticmethod
    def _select_users_who_liked_single(history_id: int):
        return (
            select(User)
            .join(HistoryLike, HistoryLike.user_id == User.id)
            .where(HistoryLike.history_id == history_id)
        )

    @staticmethod
    def _select_users_who_disliked_histories(history_ids: List[int]):
        return (
            select(HistoryDislike.history_id, User)
            .join(User, HistoryDislike.user_id == User.id)
            .where(HistoryDislike.history_id.in_(history_ids))
        )

    @staticmethod
    def _select_users_who_disliked_single(history_id: int):
        return (
            select(User)
            .join(HistoryDislike, HistoryDislike.user_id == User.id)
            .where(HistoryDislike.history_id == history_id)
        )

    # Comments Count Query Builder - StaticMethod

    @staticmethod
    def _select_comments_count_for_histories(history_ids: List[int]):
        return (
            select(Comment.history_id, func.count(Comment.id))
            .where(Comment.history_id.in_(history_ids))
            .group_by(Comment.history_id)
        )

    # Histories Fetch helpers

    async def _fetch_histories_with_author(self, skip: int, limit: int = 10) -> List[History]:
        async with self.manager.get_async_session() as session:
            result = await session.execute(
                HistoryManager._select_with_author()
                .join(HistoryScore, HistoryScore.history_id == History.id, isouter=True)
                .order_by(
                    desc(func.coalesce(HistoryScore.score, 0.0)),
                    desc(History.created_at))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())

    async def _fetch_histories_by_author_with_author(self,
                                                     author_id: int,
                                                     skip: int,
                                                     limit: int) -> List[History]:
        async with self.manager.get_async_session() as session:
            result = await session.execute(
                HistoryManager._select_with_author_by_author_id(author_id)
                .join(HistoryScore, HistoryScore.history_id == History.id, isouter=True)
                .order_by(
                    desc(func.coalesce(HistoryScore.score, 0.0)),
                    desc(History.created_at))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())

    async def _fetch_histories_by_authors_with_author(self,
                                                      author_ids: List[int],
                                                      skip: int,
                                                      limit: int) -> List[History]:
        if not author_ids:
            return []
        async with self.manager.get_async_session() as session:
            result = await session.execute(
                select(History)
                .options(joinedload(History.author))
                .where(History.author_id.in_(author_ids))
                .join(HistoryScore, HistoryScore.history_id == History.id, isouter=True)
                .order_by(
                    desc(func.coalesce(HistoryScore.score, 0.0)),
                    desc(History.created_at))
                .offset(skip)
                .limit(limit)
            )
            return list(result.scalars().all())
    
    async def _fetch_histories_by_author_id(self, author_id: int) -> List[History]:
        try:
            async with self.manager.get_async_session() as session:
                result = await session.execute(
                    HistoryManager._select_by_author_id(author_id).order_by(desc(History.created_at))
                )
                return list(result.scalars().all())
        except Exception as e:
            app_logger.exception(f"Истории с author_id {author_id} не найдены")
            raise DatabaseError(f"Истории с author_id {author_id} не найдены")

    # History Fetch Helpers

    async def _fetch_history_by_id_with_author(self, id: int) -> Optional[History]:
        async with self.manager.get_async_session() as session:
            result = await session.execute(HistoryManager._select_with_author_by_id(id))
            return result.scalars().first()

    async def _fetch_history_by_id(self, id: int) -> Optional[History]:
        try:
            async with self.manager.get_async_session() as session:
                result = await session.execute(select(History).where(History.id == id))
                return result.scalars().first()
        except Exception as e:
            app_logger.exception(f"История с id {id} не найдена")
            raise DatabaseError(f"История с id {id} не найдена")

    # Builders / Maps

    async def _get_like_dislike_maps(self, history_ids: List[int]) -> Tuple[Dict[int, int], Dict[int, int]]:
        try:
            likes_map = await self._fetch_count_map(HistoryLike, history_ids)
            dislikes_map = await self._fetch_count_map(HistoryDislike, history_ids)
            return likes_map, dislikes_map
        except Exception as e:
            app_logger.exception(f"Ошибка при получении карты лайков/дизлайков: {e}")
            raise DatabaseError(f"Ошибка при получении карты лайков/дизлайков")

    async def _get_single_like_dislike_counts(self, history_id: int) -> Tuple[int, int]:
        try:
            likes_count = await self._fetch_count(HistoryLike, history_id)
            dislikes_count = await self._fetch_count(HistoryDislike, history_id)
            return likes_count, dislikes_count
        except Exception as e:
            app_logger.exception(f"Ошибка при получении количества лайков/дизлайков для истории {history_id}: {e}")
            raise DatabaseError(f"Ошибка при получении количества лайков/дизлайков")

    async def _build_histories_with_counts(self,
                                           histories: List[History],
                                           schema_class: type[T],
                                           me_user_id: Optional[int] = None) -> List[T]:
        history_ids = [h.id for h in histories]
        likes_map, dislikes_map = await self._get_like_dislike_maps(history_ids)
        comments_map = await self._fetch_comments_map(history_ids)
        liked_users_map, disliked_users_map = await self._fetch_users_maps(history_ids, me_user_id)

        return [
            schema_class.from_model_with_counts(
                history_obj=h,
                likes=likes_map.get(h.id, 0),
                dislikes=dislikes_map.get(h.id, 0),
                comments=comments_map.get(h.id, 0),
                liked_users=liked_users_map.get(h.id, []),
                disliked_users=disliked_users_map.get(h.id, []),
            ) for h in histories
        ]

    # Utility / Agregation Fetch Helpers

    async def _fetch_users_for_history(self,
                                     history_id: int,
                                     me_user_id: Optional[int]) -> Tuple[List[UserShortOutWithFollowStatus]]:
        try:
            async with self.manager.get_async_session() as session:
                liked_rows = await session.execute(
                    HistoryManager._select_users_who_liked_single(history_id))
                disliked_rows = await session.execute(
                    HistoryManager._select_users_who_disliked_single(history_id))

            liked_list = await build_user_list(liked_rows, me_user_id)
            disliked_list = await build_user_list(disliked_rows, me_user_id)

            return liked_list, disliked_list
        except Exception as e:
            app_logger.exception(f"Ошибка при получении пользователей для истории {history_id}: {e}")
            raise DatabaseError("Ошибка при получении пользователей для истории")
    
    async def _fetch_users_maps(self,
                                history_ids: List[int],
                                me_user_id: Optional[int]) -> Tuple[Dict[int, List[UserShortOutWithFollowStatus]]]:
        try:
            async with self.manager.get_async_session() as session:
                liked_rows = await session.execute(
                    HistoryManager._select_users_who_liked_histories(history_ids))
                disliked_rows = await session.execute(
                    HistoryManager._select_users_who_disliked_histories(history_ids))

            liked_users_map = await build_users_map(liked_rows, me_user_id)
            disliked_users_map = await build_users_map(disliked_rows, me_user_id)

            return liked_users_map, disliked_users_map
        except Exception as e:
            app_logger.exception(f"Ошибка при получении пользователей лайков/дизлайков: {e}")
            raise DatabaseError("Ошибка при получении пользователей лайков/дизлайков")

    async def _fetch_count_map(self, model, history_ids: List[int]) -> Dict[int, int]:
        async with self.manager.get_async_session() as session:
            result = await session.execute(HistoryManager._select_like_count_map(model, history_ids))
            return {hid: int(cnt) for hid, cnt in result.all()}

    async def _fetch_count(self, model, history_id: int) -> int:
        async with self.manager.get_async_session() as session:
            result = await session.execute(select(func.count(model.id)).where(model.history_id == history_id))
            return int(result.scalar_one() or 0)

    async def _fetch_comments_map(self, history_ids: List[int]) -> Dict[int, int]:
        async with self.manager.get_async_session() as session:
            result = await session.execute(HistoryManager._select_comments_count_for_histories(history_ids))
            return {hid: int(cnt) for hid, cnt in result.all()}

    # Main Public Methods

    async def get_histories(self,
                            skip: int,
                            limit: int = 10,
                            me_user_id: Optional[int] = None) -> List[HistoryOut]:
        try:
            histories = await self._fetch_histories_with_author(skip, limit)
            if not histories:
                return []
            
            return await self._build_histories_with_counts(histories, HistoryOut, me_user_id)
        except Exception as e:
            app_logger.exception(f"Ошибка при получении историй {e}")
            raise DatabaseError(f"Ошибка при получении историй")

    async def get_histories_by_author_id(self,
                                         author_id: int,
                                         skip: int = 0,
                                         limit: int = 5,
                                         me_user_id: Optional[int] = None) -> List[HistoryOutShort]:
        try:
            cached = await HistoriesByAuthorCacheService.get_histories(author_id=author_id,
                                        skip=skip, limit=limit, me_user_id=me_user_id or 0)
            if cached is not None:
                return cached

            histories = await self._fetch_histories_by_author_with_author(author_id, skip, limit)
            if not histories:
                return []

            result = await self._build_histories_with_counts(histories, HistoryOutShort, me_user_id)
            await HistoriesByAuthorCacheService.set_histories(author_id=author_id,
                  skip=skip, limit=limit, me_user_id=me_user_id or 0, data=result)
            return result
        except Exception as e:
            app_logger.exception(f"Ошибка при получении историй пользователя {author_id}: {e}")
            raise DatabaseError(f"Ошибка при получении историй пользователя")

    async def get_histories_with_author_by_author_id(self,
                                                     author_id: int,
                                                     skip: int = 0,
                                                     limit: int = 5,
                                                     me_user_id: Optional[int] = None) -> List[HistoryOut]:
        try:
            histories = await self._fetch_histories_by_author_with_author(author_id, skip, limit)
            if not histories:
                return []
            return await self._build_histories_with_counts(histories, HistoryOut, me_user_id)
        except Exception as e:
            app_logger.exception(f"Ошибка при получении историй пользователя (с автором) {author_id}: {e}")
            raise DatabaseError(f"Ошибка при получении историй пользователя")

    async def get_friends_histories(self,
                                    user_id: int,
                                    friends_ids: List[int],
                                    skip: int = 0,
                                    limit: int = 10,
                                    me_user_id: Optional[int] = None) -> List[HistoryOut]:
        try:
            cached = await FriendsHistoriesCacheService.get_histories(
                user_id=user_id, skip=skip, limit=limit, me_user_id=me_user_id or 0
            )
            if cached is not None:
                return cached

            histories: List[History] = await self._fetch_histories_by_authors_with_author(friends_ids, skip, limit)
            if not histories:
                await FriendsHistoriesCacheService.set_histories(
                    user_id=user_id, skip=skip, limit=limit, me_user_id=me_user_id or 0, data=[]
                )
                return []

            result = await self._build_histories_with_counts(histories, HistoryOut, me_user_id)
            await FriendsHistoriesCacheService.set_histories(
                user_id=user_id, skip=skip, limit=limit, me_user_id=me_user_id or 0, data=result
            )
            return result
        except Exception as e:
            app_logger.exception(f"Ошибка при получении историй друзей пользователя {user_id}: {e}")
            raise DatabaseError(f"Ошибка при получении историй друзей пользователя")

    async def get_following_histories(self,
                                      user_id: int,
                                      following_user_ids: List[int],
                                      skip: int = 0,
                                      limit: int = 10,
                                      me_user_id: Optional[int] = None) -> List[HistoryOut]:
        try:
            cached = await FollowingHistoriesCacheService.get_histories(
                user_id=user_id, skip=skip, limit=limit, me_user_id=me_user_id or 0
            )
            if cached is not None:
                return cached

            histories: List[History] = await self._fetch_histories_by_authors_with_author(
                following_user_ids, skip, limit
            )

            if not histories:
                await FollowingHistoriesCacheService.set_histories(
                    user_id=user_id, skip=skip, limit=limit, me_user_id=me_user_id or 0, data=[]
                )
                return []

            result = await self._build_histories_with_counts(histories, HistoryOut, me_user_id)
            await FollowingHistoriesCacheService.set_histories(
                user_id=user_id, skip=skip, limit=limit, me_user_id=me_user_id or 0, data=result
            )
            return result
        except Exception as e:
            app_logger.exception(f"Ошибка при получении историй подписок пользователя {user_id}: {e}")
            raise DatabaseError(f"Ошибка при получении историй подписок пользователя")

    async def get_history_by_id(self, id: int, me_user_id: Optional[int] = None) -> HistoryOut | None:
        try:
            cached = await HistoryCacheService.get_history_with_counts(history_id=id, me_user_id=me_user_id or 0)
            if cached is not None:
                return cached

            history = await self._fetch_history_by_id_with_author(id)
            if not history:
                return None

            likes, dislikes = await self._get_single_like_dislike_counts(id)
            liked_users, disliked_users = await self._fetch_users_for_history(id, me_user_id)
            comments_map = await self._fetch_comments_map([id])
            
            result = HistoryOut.from_model_with_counts(
                history_obj=history,
                likes=likes,
                dislikes=dislikes,
                comments=comments_map.get(id, 0),
                liked_users=liked_users,
                disliked_users=disliked_users,
            )
            await HistoryCacheService.set_history_with_counts(history_id=id, me_user_id=me_user_id or 0, history_data=result)
            return result
        except Exception as e:
            app_logger.exception(f"Ошибка при получении истории {id}: {e}")
            raise DatabaseError(f"Ошибка при получении истории")
            
    async def create_history(self, history_obj: History) -> HistoryOut:
        try:
            async with self.manager.get_async_session() as session:
                session.add(history_obj)
                await session.commit()
                result = await session.execute(HistoryManager._select_with_author_by_id(history_obj.id))
                history_with_author = result.scalars().first()
                
                # Для новой истории counts всегда равны 0, но получаем реальные значения для консистентности
                likes_map = await self._fetch_count_map(HistoryLike, [history_obj.id])
                dislikes_map = await self._fetch_count_map(HistoryDislike, [history_obj.id])
                comments_map = await self._fetch_comments_map([history_obj.id])
                
                # Используем from_model_with_counts вместо model_validate для консистентности
                out = HistoryOut.from_model_with_counts(
                    history_obj=history_with_author,
                    likes=likes_map.get(history_obj.id, 0),
                    dislikes=dislikes_map.get(history_obj.id, 0),
                    comments=comments_map.get(history_obj.id, 0),
                    liked_users=[],  # Новая история не может иметь лайков
                    disliked_users=[]  # Новая история не может иметь дизлайков
                )
                
                await HistoryCacheService.invalidate_history_cache(history_obj.id)
                await HistoriesByAuthorCacheService.invalidate_histories(out.author.id if hasattr(out, 'author') and out.author else history_obj.author_id)
                # Initial score compute for the newly created history
                await ScoreService.recompute_for_history_id(history_obj.id)
                return out
        except Exception as e:
            app_logger.exception(f"Ошибка при создании истории: {e}")
            raise DatabaseError(f"Ошибка при создании истории") 

    async def delete_history(self, id: int) -> HistoryOut:
        try:
            async with self.manager.get_async_session() as session:
                result = await session.execute(HistoryManager._select_with_author_by_id(id))
                history = result.scalars().first()
                if not history:
                    raise HistoryNotFoundError()
                await session.delete(history)
                await session.commit()
                out = HistoryOut.model_validate(history)
                await HistoryCacheService.invalidate_history_cache(id)
                await HistoriesByAuthorCacheService.invalidate_histories(out.author.id if hasattr(out, 'author') and out.author else history.author_id)
                return out
        except Exception as e:
            app_logger.exception(f"Ошибка при удалении истории {id}: {e}")
            raise DatabaseError(f"Ошибка при удалении истории")
