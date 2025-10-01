from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.future import select

from core.logger import app_logger

from database.managers.session_manager import Manager
from database.managers.user_block_manager import UserBlockManager
from database.models.followers import Follower

from exceptions.base import DatabaseError
from exceptions.base import ModelNotFoundError
from exceptions.follows import FollowAlredyExists

from services.cache_service import FollowersCacheService
from services.cache_invalidation_service import CacheInvalidationService

class FollowersManager:
    def __init__(self):
        self.manager = Manager()
        self._model = Follower
        self.user_block_manager = UserBlockManager()

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
        # Проверяем, не заблокированы ли пользователи друг другом
        is_follower_blocked = await self.user_block_manager.is_user_blocked(blocker_id=target_id, blocked_user_id=follower_id)
        is_target_blocked = await self.user_block_manager.is_user_blocked(blocker_id=follower_id, blocked_user_id=target_id)
        
        if is_follower_blocked or is_target_blocked:
            app_logger.warning_event("follow_denied_user_blocked", 
                                   follower_id=follower_id, 
                                   target_id=target_id,
                                   follower_blocked=is_follower_blocked,
                                   target_blocked=is_target_blocked)
            raise DatabaseError("Нельзя подписаться на заблокированного пользователя")
            
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
            # Фильтруем заблокированных пользователей из кэша
            filtered_followers = []
            for follower in cached:
                is_blocked = await self.user_block_manager.is_user_blocked(blocker_id=user_id, blocked_user_id=follower.follower_id)
                if not is_blocked:
                    filtered_followers.append(follower)
            return filtered_followers
            
        async with self.manager.get_async_session() as session:
            try:
                result = await session.execute(FollowersManager._select_followers(user_id).offset(skip).limit(limit))
                rows = result.scalars().all()
                
                # Фильтруем заблокированных пользователей
                filtered_followers = []
                for follower in rows:
                    is_blocked = await self.user_block_manager.is_user_blocked(blocker_id=user_id, blocked_user_id=follower.follower_id)
                    if not is_blocked:
                        filtered_followers.append(follower)
                
                await FollowersCacheService.set_followers(user_id=user_id, skip=skip, limit=limit, data=filtered_followers)
                return filtered_followers
            except Exception:   
                app_logger.error_event("get_followers_failed", user_id=user_id, skip=skip, limit=limit)
                raise DatabaseError(f"Ошибка при получении подписчиков user_id={user_id}")

    async def get_following(self, user_id: int, skip: int = 0, limit: int = 100):
        cached = await FollowersCacheService.get_following(user_id=user_id, skip=skip, limit=limit)
        if cached is not None:
            # Фильтруем заблокированных пользователей из кэша
            filtered_following = []
            for following in cached:
                is_blocked = await self.user_block_manager.is_user_blocked(blocker_id=user_id, blocked_user_id=following.user_id)
                if not is_blocked:
                    filtered_following.append(following)
            return filtered_following
            
        async with self.manager.get_async_session() as session:
            try:
                result = await session.execute(FollowersManager._select_following(user_id).offset(skip).limit(limit))
                rows = result.scalars().all()
                
                # Фильтруем заблокированных пользователей
                filtered_following = []
                for following in rows:
                    is_blocked = await self.user_block_manager.is_user_blocked(blocker_id=user_id, blocked_user_id=following.user_id)
                    if not is_blocked:
                        filtered_following.append(following)
                
                await FollowersCacheService.set_following(user_id=user_id, skip=skip, limit=limit, data=filtered_following)
                return filtered_following
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
