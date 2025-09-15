"""Сервисы кэширования.

В проекте используется Redis как быстрый in-memory кэш для разных наборов данных:
- карточки пользователей
- истории и агрегированные счётчики по ним
- списки подписчиков/подписок и друзей
- результаты поиска пользователей

Ключевые принципы:
- Сохранение структур — через pickle с самым новым протоколом (быстро и компактно).
- Ключи формируются детерминированно и сегментируются по префиксам, чтобы можно было делать
  целевую инвалидацию через scan+delete.
- TTL подобран по типу данных (истории/списки обычно 1–5 минут, профили — дольше).

Предупреждение:
- Pickle небезопасен для данных из недоверенных источников. Здесь мы кэшируем только
  собственные объекты сервиса — это безопасно. Если нужно отдавать кэш наружу, следует
  заменить сериализацию на JSON/Pydantic.
"""

from __future__ import annotations
import pickle

from typing import Any

from core.logger import app_logger
from core.config import settings

from redis.asyncio import Redis
from redis.exceptions import ConnectionError, RedisError

_redis_client: Redis | None = None
_redis_available: bool | None = None

def get_redis_client() -> Redis:
    global _redis_client
    if _redis_client is None:
        _redis_client = Redis.from_url(settings.redis_url, decode_responses=False)
    return _redis_client

async def is_redis_available() -> bool:
    """Check if Redis is available and cache the result."""
    global _redis_available
    
    # Check if Redis is disabled in config
    if not settings.redis_enabled:
        if _redis_available is None:
            app_logger.info("Redis caching is disabled in configuration")
        _redis_available = False
        return False
    
    if _redis_available is None:
        try:
            client = get_redis_client()
            await client.ping()
            _redis_available = True
            app_logger.info("Redis connection established successfully")
        except (ConnectionError, RedisError) as e:
            _redis_available = False
            app_logger.warning(f"Redis not available: {e}. Running without cache.")
        except Exception as e:
            _redis_available = False
            app_logger.warning(f"Unexpected error connecting to Redis: {e}. Running without cache.")
    return _redis_available

class RedisCache:
    """Базовая обёртка над Redis для сериализации/десериализации пиклем.

    Используется внутренне сервисами, чтобы унифицировать формат хранения и
    упростить логику работы с TTL и инвалидацией.
    """
    @staticmethod
    async def get(key: str) -> Any | None:
        if not await is_redis_available():
            return None
        
        try:
            client = get_redis_client()
            raw = await client.get(key)
            if raw is None:
                return None
            return pickle.loads(raw)
        except (ConnectionError, RedisError):
            # Redis connection lost, mark as unavailable
            global _redis_available
            _redis_available = False
            app_logger.warning(f"Redis connection lost during get operation for key: {key}")
            return None
        except Exception:
            app_logger.exception(f"Redis deserialization error for key: {key}")
            return None

    @staticmethod
    async def set(key: str, value: Any, ttl: int = 300) -> None:
        """Установить значение с TTL (в секундах)."""
        if not await is_redis_available():
            return
        
        try:
            client = get_redis_client()
            data = pickle.dumps(value, protocol=pickle.HIGHEST_PROTOCOL)
            await client.set(name=key, value=data, ex=ttl)
        except (ConnectionError, RedisError):
            # Redis connection lost, mark as unavailable
            global _redis_available
            _redis_available = False
            app_logger.warning(f"Redis connection lost during set operation for key: {key}")
        except Exception:
            app_logger.exception(f"Redis serialization error for key: {key}")

    @staticmethod
    async def delete_by_prefix(prefix: str) -> None:
        """Удалить все ключи, начинающиеся с префикса.

        Использует scan_iter, чтобы не блокировать Redis большим KEYS.
        """
        if not await is_redis_available():
            return
            
        try:
            client = get_redis_client()
            pattern = f"{prefix}*"
            keys_to_delete = []
            async for key in client.scan_iter(match=pattern, count=500):
                keys_to_delete.append(key)
                if len(keys_to_delete) >= 1000:
                    await client.delete(*keys_to_delete)
                    keys_to_delete.clear()
            if keys_to_delete:
                await client.delete(*keys_to_delete)
        except (ConnectionError, RedisError):
            # Redis connection lost, mark as unavailable
            global _redis_available
            _redis_available = False
            app_logger.warning(f"Redis connection lost during delete operation for prefix: {prefix}")
        except Exception:
            app_logger.exception(f"Redis delete error for prefix: {prefix}")

class UserCacheService:
    """Специализированный кэш для пользовательских данных.

    Ключ дополняется идентификатором "me_user_id", так как часть полей
    (например, follow_status) зависит от текущего пользователя.
    """
    
    @staticmethod
    async def get_user_info(user_id: int, me_user_id: int) -> Any | None:
        """Получить информацию о пользователе из кэша"""
        cache_key = f"user_info:{user_id}:{me_user_id}"
        return await RedisCache.get(cache_key)

    @staticmethod
    async def set_user_info(user_id: int, me_user_id: int, user_info: Any, ttl: int = 600) -> None:
        """Кэшировать информацию о пользователе"""
        cache_key = f"user_info:{user_id}:{me_user_id}"
        await RedisCache.set(cache_key, user_info, ttl)

    @staticmethod
    async def invalidate_user_cache(user_id: int) -> None:
        """Инвалидировать кэш пользователя"""
        await RedisCache.delete_by_prefix(f"user_info:{user_id}:")

class HistoryCacheService:
    """Специализированный кэш для историй с агрегированными счётчиками."""
    
    @staticmethod
    async def get_history_with_counts(history_id: int,
                                      me_user_id: int) -> Any | None:
        """Получить историю с подсчетами из кэша"""
        cache_key = f"history_with_counts:{history_id}:{me_user_id}"
        return await RedisCache.get(cache_key)

    @staticmethod
    async def set_history_with_counts(history_id: int,
                                      me_user_id: int,
                                      history_data: Any,
                                      ttl: int = 300) -> None:
        """Кэшировать историю с подсчетами"""
        cache_key = f"history_with_counts:{history_id}:{me_user_id}"
        await RedisCache.set(cache_key, history_data, ttl)

    @staticmethod
    async def invalidate_history_cache(history_id: int) -> None:
        """Инвалидировать кэш истории"""
        await RedisCache.delete_by_prefix(f"history_with_counts:{history_id}:")

class HistoryScoreCacheService:
    """Кэш для сохранённых значений score по историям."""
    @staticmethod
    async def get_score(history_id: int) -> float | None:
        key = f"history_score:{history_id}"
        value = await RedisCache.get(key)
        if value is None:
            return None
        try:
            return float(value)
        except Exception:
            return None

    @staticmethod
    async def set_score(history_id: int,
                        score: float,
                        ttl: int = 600) -> None:
        key = f"history_score:{history_id}"
        await RedisCache.set(key, float(score), ttl)

    @staticmethod
    async def invalidate_score(history_id: int) -> None:
        await RedisCache.delete_by_prefix(f"history_score:{history_id}")

class FollowersCacheService:
    """Кэш для списков подписчиков/подписок."""
    @staticmethod
    async def get_followers(user_id: int,
                            skip: int,
                            limit: int):
        return await RedisCache.get(f"followers:{user_id}:{skip}:{limit}")

    @staticmethod
    async def set_followers(user_id: int,
                            skip: int,
                            limit: int,
                            data: Any,
                            ttl: int = 120):
        await RedisCache.set(f"followers:{user_id}:{skip}:{limit}", data, ttl)

    @staticmethod
    async def invalidate_followers(user_id: int):
        await RedisCache.delete_by_prefix(f"followers:{user_id}:")

    @staticmethod
    async def get_following(user_id: int,
                            skip: int,
                            limit: int):
        return await RedisCache.get(f"following:{user_id}:{skip}:{limit}")

    @staticmethod
    async def set_following(user_id: int,
                            skip: int,
                            limit: int,
                            data: Any,
                            ttl: int = 120):
        await RedisCache.set(f"following:{user_id}:{skip}:{limit}", data, ttl)

    @staticmethod
    async def invalidate_following(user_id: int):
        await RedisCache.delete_by_prefix(f"following:{user_id}:")

class FriendsCacheService:
    @staticmethod
    async def get_friends(user_id: int,
                          skip: int,
                          limit: int):
        return await RedisCache.get(f"friends:{user_id}:{skip}:{limit}")

    @staticmethod
    async def set_friends(user_id: int,
                          skip: int,
                          limit: int,
                          data: Any,
                          ttl: int = 120):
        await RedisCache.set(f"friends:{user_id}:{skip}:{limit}", data, ttl)

    @staticmethod
    async def invalidate_friends(user_id: int):
        await RedisCache.delete_by_prefix(f"friends:{user_id}:")

class HistoriesByAuthorCacheService:
    @staticmethod
    async def get_histories(author_id: int,
                            skip: int,
                            limit: int,
                            me_user_id: int):
        return await RedisCache.get(f"histories_by_author:{author_id}:{skip}:{limit}:{me_user_id}")

    @staticmethod
    async def set_histories(author_id: int,
                            skip: int,
                            limit: int,
                            me_user_id: int,
                            data: Any,
                            ttl: int = 120):
        await RedisCache.set(f"histories_by_author:{author_id}:{skip}:{limit}:{me_user_id}", data, ttl)

    @staticmethod
    async def invalidate_histories(author_id: int):
        await RedisCache.delete_by_prefix(f"histories_by_author:{author_id}:")


class FriendsHistoriesCacheService:
    """Кэш результирующих списков историй друзей пользователя."""
    @staticmethod
    async def get_histories(user_id: int,
                            skip: int,
                            limit: int,
                            me_user_id: int):
        return await RedisCache.get(f"friends_histories:{user_id}:{skip}:{limit}:{me_user_id}")

    @staticmethod
    async def set_histories(user_id: int,
                            skip: int,
                            limit: int,
                            me_user_id: int,
                            data: Any,
                            ttl: int = 120):
        await RedisCache.set(f"friends_histories:{user_id}:{skip}:{limit}:{me_user_id}", data, ttl)

    @staticmethod
    async def invalidate_histories(user_id: int):
        await RedisCache.delete_by_prefix(f"friends_histories:{user_id}:")

class FollowingHistoriesCacheService:
    """Кэш результирующих списков историй подписок пользователя."""
    @staticmethod
    async def get_histories(user_id: int,
                            skip: int,
                            limit: int,
                            me_user_id: int):
        return await RedisCache.get(f"following_histories:{user_id}:{skip}:{limit}:{me_user_id}")

    @staticmethod
    async def set_histories(user_id: int,
                            skip: int,
                            limit: int,
                            me_user_id: int,
                            data: Any,
                            ttl: int = 120):
        await RedisCache.set(f"following_histories:{user_id}:{skip}:{limit}:{me_user_id}", data, ttl)

    @staticmethod
    async def invalidate_histories(user_id: int):
        await RedisCache.delete_by_prefix(f"following_histories:{user_id}:")

class UsersSearchCacheService:
    @staticmethod
    async def get_search(query: str,
                         skip: int,
                         limit: int,
                         me_user_id: int):
        return await RedisCache.get(f"users_search:{me_user_id}:{query}:{skip}:{limit}")

    @staticmethod
    async def set_search(query: str,
                         skip: int,
                         limit: int,
                         me_user_id: int,
                         data: Any,
                         ttl: int = 60):
        await RedisCache.set(f"users_search:{me_user_id}:{query}:{skip}:{limit}", data, ttl)

    @staticmethod
    async def invalidate_for_user(me_user_id: int):
        await RedisCache.delete_by_prefix(f"users_search:{me_user_id}:")

class CommentsByHistoryCacheService:
    @staticmethod
    async def get_comments(history_id: int,
                           skip: int,
                           limit: int,
                           me_user_id: int):
        return await RedisCache.get(f"comments_by_history:{history_id}:{skip}:{limit}:{me_user_id}")

    @staticmethod
    async def set_comments(history_id: int,
                           skip: int,
                           limit: int,
                           me_user_id: int,
                           data: Any,
                           ttl: int = 60):
        await RedisCache.set(f"comments_by_history:{history_id}:{skip}:{limit}:{me_user_id}", data, ttl)

    @staticmethod
    async def invalidate_comments(history_id: int):
        await RedisCache.delete_by_prefix(f"comments_by_history:{history_id}:")
