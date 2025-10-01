"""Менеджер друзей (friends).

Дружба создаётся только при взаимной подписке двух пользователей. Менеджер
реализует добавление/удаление дружбы, выборку друзей с кэшем и корректную
инвалидацию зависимых кэшей.
"""
from sqlalchemy import and_
from sqlalchemy.future import select

from core.logger import app_logger

from database.managers.followers_manager import FollowersManager
from database.managers.session_manager import Manager
from database.managers.user_block_manager import UserBlockManager
from database.models.friends import Friend

from exceptions.base import DatabaseError
from exceptions.base import ModelNotFoundError

from services.cache_service import FriendsCacheService
from services.cache_invalidation_service import CacheInvalidationService

class FriendsManager:
    def __init__(self):
        self.manager = Manager()
        self._model = Friend
        self.followers_manager = FollowersManager()
        self.user_block_manager = UserBlockManager()

    @staticmethod
    def _select_friendship(user_id: int, friend_id: int):
        """Выборка дружбы по ID пользователей."""
        return select(Friend).where(
            and_(Friend.user_id == min(user_id, friend_id), Friend.friend_id == max(user_id, friend_id))
        )

    @staticmethod
    def _select_friends(user_id: int):
        """Выборка друзей по ID пользователя."""
        return select(Friend).where(
            (Friend.user_id == user_id) | (Friend.friend_id == user_id)
        )

    async def add_friend(self, user_id: int, friend_id: int) -> Friend | None:
        """Добавить дружбу между двумя пользователями."""
        # Проверяем, не заблокированы ли пользователи друг другом
        is_user_blocked = await self.user_block_manager.is_user_blocked(blocker_id=user_id, blocked_user_id=friend_id)
        is_friend_blocked = await self.user_block_manager.is_user_blocked(blocker_id=friend_id, blocked_user_id=user_id)
        
        if is_user_blocked or is_friend_blocked:
            app_logger.warning_event("friend_add_denied_user_blocked", 
                                     user_id=user_id, 
                                     friend_id=friend_id,
                                     user_blocked=is_user_blocked,
                                     friend_blocked=is_friend_blocked)
            return None
            
        is_user_following = await self.followers_manager.check_mutual_follow(target_id=friend_id, follower_id=user_id)
        is_friend_following = await self.followers_manager.check_mutual_follow(target_id=user_id, follower_id=friend_id)
        if not (is_user_following and is_friend_following):
            app_logger.warning_event("friend_add_denied_no_mutual_follow", user_id=user_id, friend_id=friend_id)
            return None
        async with self.manager.get_async_session() as session:
            try:
                friendship = Friend(user_id=min(user_id, friend_id), friend_id=max(user_id, friend_id))
                session.add(friendship)
                await session.commit()
                await session.refresh(friendship)
                app_logger.info_event("friend_added", user_id=user_id, friend_id=friend_id)
                # Правильная инвалидация вместо записи None
                await FriendsCacheService.invalidate_friends(user_id)
                await FriendsCacheService.invalidate_friends(friend_id)
                # Также инвалидация карточек пользователей, так как follow_status может измениться
                await CacheInvalidationService.on_friend_changed(user_id)
                await CacheInvalidationService.on_friend_changed(friend_id)
                return friendship
            except Exception:
                await session.rollback()
                app_logger.error_event("friend_add_failed", user_id=user_id, friend_id=friend_id)
                raise DatabaseError(f"Ошибка при добавлении в друзья user_id={user_id}, friend_id={friend_id}")

    async def remove_friend(self, user_id: int, friend_id: int) -> None:
        """Удалить дружбу между двумя пользователями."""
        async with self.manager.get_async_session() as session:
            try:
                result = await session.execute(FriendsManager._select_friendship(user_id, friend_id))
                friendship = result.scalars().first()
                if not friendship:
                    app_logger.warning_event("friend_remove_not_found", user_id=user_id, friend_id=friend_id)
                    raise ModelNotFoundError(f"Дружба между {user_id} и {friend_id} не найдена.")
                await session.delete(friendship)
                await session.commit()
                app_logger.info_event("friend_removed", user_id=user_id, friend_id=friend_id)
                await FriendsCacheService.invalidate_friends(user_id)
                await FriendsCacheService.invalidate_friends(friend_id)
            except Exception:
                await session.rollback()
                app_logger.error_event("friend_remove_failed", user_id=user_id, friend_id=friend_id)
                raise DatabaseError(f"Ошибка при удалении из друзей user_id={user_id}, friend_id={friend_id}")

    async def get_friends(self, user_id: int, skip: int = 0, limit: int = 100) -> list[Friend]:
        """Получить друзей пользователя с кэшем."""
        cached = await FriendsCacheService.get_friends(user_id=user_id, skip=skip, limit=limit)
        if cached is not None:
            # Фильтруем заблокированных пользователей из кэша
            filtered_friends = []
            for friendship in cached:
                friend_id = friendship.friend_id if friendship.user_id == user_id else friendship.user_id
                is_blocked = await self.user_block_manager.is_user_blocked(blocker_id=user_id, blocked_user_id=friend_id)
                if not is_blocked:
                    filtered_friends.append(friendship)
            return filtered_friends
            
        async with self.manager.get_async_session() as session:
            try:
                result = await session.execute(FriendsManager._select_friends(user_id).offset(skip).limit(limit))
                rows = result.scalars().all()
                
                # Фильтруем заблокированных пользователей
                filtered_friends = []
                for friendship in rows:
                    friend_id = friendship.friend_id if friendship.user_id == user_id else friendship.user_id
                    is_blocked = await self.user_block_manager.is_user_blocked(blocker_id=user_id, blocked_user_id=friend_id)
                    if not is_blocked:
                        filtered_friends.append(friendship)
                
                await FriendsCacheService.set_friends(user_id=user_id, skip=skip, limit=limit, data=filtered_friends)
                return filtered_friends
            except Exception:
                app_logger.error_event("get_friends_failed", user_id=user_id, skip=skip, limit=limit)
                raise DatabaseError(f"Ошибка при получении друзей user_id={user_id}")
