"""Централизованная инвалидация кэшей.

Обязанности:
- По событиям данных (история, лайк/дизлайк, подписка, дружба, комментарий)
  инвалидировать только релевантные ключи кэша.
- Согласованность: исключить ситуации, когда кэш возвращает устаревшие данные.
"""

from __future__ import annotations

from services.cache_service import CommentsByHistoryCacheService
from services.cache_service import FriendsHistoriesCacheService
from services.cache_service import FriendsCacheService
from services.cache_service import FollowersCacheService
from services.cache_service import HistoryCacheService
from services.cache_service import HistoriesByAuthorCacheService
from services.cache_service import FollowingHistoriesCacheService
from services.cache_service import UsersSearchCacheService
from services.cache_service import UserCacheService
from services.cache_service import HistoryScoreCacheService

class CacheInvalidationService:
    @staticmethod
    async def on_reaction_changed(history_id: int | None = None,
                                  comment_author_ids: list[int] | None = None,
                                  me_user_id: int | None = None):
        """Инвалидация при изменении реакции (лайк/дизлайк).

        - История: counters могли измениться
        - Авторы комментариев: их карточки могли измениться (косвенно)
        - Текущий пользователь: его карточка/статусы
        """
        if history_id is not None:
            await HistoryCacheService.invalidate_history_cache(history_id)
            await HistoryScoreCacheService.invalidate_score(history_id)
        if comment_author_ids:
            for uid in comment_author_ids:
                await UserCacheService.invalidate_user_cache(uid)
        if me_user_id is not None:
            await UserCacheService.invalidate_user_cache(me_user_id)

    @staticmethod
    async def on_history_changed(history_id: int, author_id: int):
        """Инвалидация при создании/обновлении/удалении истории."""
        await HistoryCacheService.invalidate_history_cache(history_id)
        await HistoryScoreCacheService.invalidate_score(history_id)
        await UserCacheService.invalidate_user_cache(author_id)
        await HistoriesByAuthorCacheService.invalidate_histories(author_id)

    @staticmethod
    async def on_user_changed(user_id: int):
        """Инвалидация карточки пользователя и списков его историй."""
        await UserCacheService.invalidate_user_cache(user_id)
        await HistoriesByAuthorCacheService.invalidate_histories(user_id)

    @staticmethod
    async def on_comment_changed(history_id: int):
        """Инвалидация списка комментариев и кэша истории."""
        await CommentsByHistoryCacheService.invalidate_comments(history_id)
        await HistoryCacheService.invalidate_history_cache(history_id)

    @staticmethod
    async def on_friend_changed(user_id: int):
        """Инвалидация кэшей друзей и их историй для пользователя."""
        await FriendsCacheService.invalidate_friends(user_id)
        await FriendsHistoriesCacheService.invalidate_histories(user_id)

    @staticmethod
    async def on_follow_changed(user_id: int, follower_id: int):
        """Инвалидация при подписке/отписке.

        Актуализируются: карточки обоих пользователей, списки подписчиков/подписок,
        списки друзей (возможна дружба при взаимной подписке), истории по подпискам,
        а также результаты поиска (учитывается follow_status).
        """
        # Профили и карточки пользователей для обоих участников
        await UserCacheService.invalidate_user_cache(user_id)
        await UserCacheService.invalidate_user_cache(follower_id)
        # Листы подписчиков/подписок для обоих
        await FollowersCacheService.invalidate_followers(user_id)
        await FollowersCacheService.invalidate_following(user_id)
        await FollowersCacheService.invalidate_followers(follower_id)
        await FollowersCacheService.invalidate_following(follower_id)
        # Друзья потенциально меняются при взаимной подписке
        await FriendsCacheService.invalidate_friends(user_id)
        await FriendsCacheService.invalidate_friends(follower_id)
        # Истории подписок для обоих
        await FollowingHistoriesCacheService.invalidate_histories(user_id)
        await FollowingHistoriesCacheService.invalidate_histories(follower_id)
        # Результаты поиска пользователей зависят от follow_status текущего пользователя
        await UsersSearchCacheService.invalidate_for_user(user_id)
        await UsersSearchCacheService.invalidate_for_user(follower_id)
