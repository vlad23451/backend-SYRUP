from core.logger import app_logger

from database.managers.session_manager import Manager
from database.models.followers import Follower

from exceptions.base import DatabaseError
from exceptions.base import ModelNotFoundError
from exceptions.follow import FollowAlredyExists

from services.cache_service import FollowersCacheService
from services.cache_invalidation_service import CacheInvalidationService

from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

class FollowersManager:
    def __init__(self):
        self.manager = Manager()
        self._model = Follower

    @staticmethod
    def _select_follow_record(target_id: int, follower_id: int):
        return select(Follower).where(
            and_(Follower.user_id == target_id, Follower.follower_id == follower_id)
        )

    @staticmethod
    def _select_followers(user_id: int):
        return select(Follower).where(Follower.user_id == user_id)

    @staticmethod
    def _select_following(user_id: int):
        return select(Follower).where(Follower.follower_id == user_id)

    async def follow(self, target_id: int, follower_id: int) -> Follower:
        async with self.manager.get_async_session() as session:
            try:
                follow = Follower(user_id=target_id, follower_id=follower_id)
                session.add(follow)
                await session.commit()
                await session.refresh(follow)
                app_logger.info_event("follow_created", follower_id=follower_id, target_id=target_id)
                # Инвалидация всех зависимых кэшей при подписке
                await CacheInvalidationService.on_follow_changed(user_id=target_id, follower_id=follower_id)
                return follow
            except IntegrityError:
                await session.rollback()
                app_logger.warning_event("follow_already_exists", follower_id=follower_id, target_id=target_id)
                raise FollowAlredyExists(f"Пользователь {follower_id} уже подписан на {target_id}")
            except Exception:
                await session.rollback()
                app_logger.error_event("follow_create_failed", follower_id=follower_id, target_id=target_id)
                raise DatabaseError(f"Ошибка при подписке follower_id={follower_id} -> target_id={target_id}")

    async def unfollow(self, target_id: int, follower_id: int) -> None:
        async with self.manager.get_async_session() as session:
            try:
                result = await session.execute(FollowersManager._select_follow_record(target_id, follower_id))
                follow = result.scalars().first()
                if not follow:
                    app_logger.warning_event("unfollow_not_found", follower_id=follower_id, target_id=target_id)
                    raise ModelNotFoundError("Подписка не найдена.")
                await session.delete(follow)
                await session.commit()
                # Инвалидация всех зависимых кэшей при отписке
                await CacheInvalidationService.on_follow_changed(user_id=target_id, follower_id=follower_id)
                app_logger.info_event("unfollow_deleted", follower_id=follower_id, target_id=target_id)
            except Exception:
                await session.rollback()
                app_logger.error_event("unfollow_failed", follower_id=follower_id, target_id=target_id)
                raise DatabaseError(f"Ошибка при отписке follower_id={follower_id} -> target_id={target_id}")

    async def get_followers(self, user_id: int, skip: int = 0, limit: int = 100):
        cached = await FollowersCacheService.get_followers(user_id=user_id, skip=skip, limit=limit)
        if cached is not None:
            return cached
        async with self.manager.get_async_session() as session:
            try:
                result = await session.execute(FollowersManager._select_followers(user_id).offset(skip).limit(limit))
                rows = result.scalars().all()
                await FollowersCacheService.set_followers(user_id=user_id, skip=skip, limit=limit, data=rows)
                return rows
            except Exception:   
                app_logger.error_event("get_followers_failed", user_id=user_id, skip=skip, limit=limit)
                raise DatabaseError(f"Ошибка при получении подписчиков user_id={user_id}")

    async def get_following(self, user_id: int, skip: int = 0, limit: int = 100):
        cached = await FollowersCacheService.get_following(user_id=user_id, skip=skip, limit=limit)
        if cached is not None:
            return cached
        async with self.manager.get_async_session() as session:
            try:
                result = await session.execute(FollowersManager._select_following(user_id).offset(skip).limit(limit))
                rows = result.scalars().all()
                await FollowersCacheService.set_following(user_id=user_id, skip=skip, limit=limit, data=rows)
                return rows
            except Exception:
                app_logger.error_event("get_following_failed", user_id=user_id, skip=skip, limit=limit)
                raise DatabaseError(f"Ошибка при получении подписок user_id={user_id}")
    
    async def check_mutual_follow(self, target_id: int, follower_id: int) -> bool:
        async with self.manager.get_async_session() as session:
            try:
                result = await session.execute(FollowersManager._select_follow_record(target_id, follower_id))
                return bool(result.scalars().first())
            except Exception:
                app_logger.error_event("check_mutual_follow_failed", follower_id=follower_id, target_id=target_id)
                raise DatabaseError(f"Ошибка при проверке подписки follower_id={follower_id} -> target_id={target_id}")
