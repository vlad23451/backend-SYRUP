from typing import List

from core.logger import app_logger

from database.managers.base_manager import BaseManager

from database.models.favorites import Favorite
from database.models.history import History

from exceptions.base import DatabaseError
from exceptions.histories import HistoryNotFoundError
from exceptions.favorites import FavoriteAlreadyExistsError
from exceptions.favorites import FavoriteNotFoundError

from schemas.favorites import FavoriteCreate
from schemas.favorites import FavoriteOut
from schemas.favorites import FavoritesResponse
from schemas.history import HistoryOut

from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload


class FavoritesManager(BaseManager[Favorite, FavoriteCreate]):
    def __init__(self) -> None:
        super().__init__(Favorite)

    async def add_to_favorites(self, user_id: int, history_id: int) -> FavoriteOut:
        async with self.manager.get_async_session() as session:
            try:
                history = await session.get(History, history_id)
                if not history:
                    app_logger.error(f"History с id {history_id} не найдена")
                    raise HistoryNotFoundError(f"History с id {history_id} не найдена")
                
                existing_favorite = await session.execute(
                    select(Favorite).where(
                        Favorite.user_id == user_id,
                        Favorite.history_id == history_id
                    )
                )
                if existing_favorite.scalar_one_or_none():
                    app_logger.warning(f"История {history_id} уже в избранном у пользователя {user_id}")
                    raise FavoriteAlreadyExistsError()
                
                favorite = Favorite(
                    user_id=user_id,
                    history_id=history_id
                )
                session.add(favorite)
                await session.commit()
                await session.refresh(favorite)
                
                app_logger.info(f"История {history_id} добавлена в избранное пользователя {user_id}")
                return FavoriteOut.model_validate(favorite)
                
            except Exception as e:
                await session.rollback()
                app_logger.exception(f"Ошибка при добавлении истории {history_id} в избранное: {e}")
                raise DatabaseError(f"Ошибка при добавлении истории в избранное")

    async def remove_from_favorites(self, user_id: int, history_id: int) -> None:
        async with self.manager.get_async_session() as session:
            try:
                result = await session.execute(
                    select(Favorite).where(
                        Favorite.user_id == user_id,
                        Favorite.history_id == history_id
                    )
                )
                favorite = result.scalar_one_or_none()
                
                if not favorite:
                    app_logger.warning(f"История {history_id} не найдена в избранном у пользователя {user_id}")
                    raise FavoriteNotFoundError()
                
                await session.delete(favorite)
                await session.commit()
                
                app_logger.info(f"История {history_id} удалена из избранного пользователя {user_id}")
                
            except Exception as e:
                await session.rollback()
                app_logger.exception(f"Ошибка при удалении истории {history_id} из избранного: {e}")
                raise DatabaseError(f"Ошибка при удалении истории из избранного")

    async def is_favorite(self, user_id: int, history_id: int) -> bool:
        try:
            async with self.manager.get_async_session() as session:
                result = await session.execute(
                    select(Favorite).where(
                        Favorite.user_id == user_id,
                        Favorite.history_id == history_id
                    )
                )
                return result.scalar_one_or_none() is not None
        except Exception as e:
            app_logger.exception(f"Ошибка при проверке избранного: {e}")
            return False

    async def get_user_favorites(self, 
                                user_id: int, 
                                skip: int = 0, 
                                limit: int = 10) -> FavoritesResponse:
        try:
            async with self.manager.get_async_session() as session:
                count_result = await session.execute(
                    select(func.count(Favorite.id)).where(Favorite.user_id == user_id)
                )
                total = count_result.scalar_one() or 0
                
                result = await session.execute(
                    select(Favorite)
                    .where(Favorite.user_id == user_id)
                    .order_by(desc(Favorite.created_at))
                    .offset(skip)
                    .limit(limit)
                )
                favorites = list(result.scalars().all())
                
                if not favorites:
                    return FavoritesResponse(
                        history_ids=[],
                        histories=[],
                        total=total,
                        skip=skip,
                        limit=limit
                    )
                
                history_ids = [fav.history_id for fav in favorites]
                
                # Получаем полные данные историй
                histories_result = await session.execute(
                    select(History)
                    .options(joinedload(History.author))
                    .where(History.id.in_(history_ids))
                )
                histories = list(histories_result.scalars().all())
                
                # Сортируем истории в том же порядке, что и избранное
                history_dict = {h.id: h for h in histories}
                ordered_histories = [history_dict[hid] for hid in history_ids if hid in history_dict]
                
                # Строим HistoryOut с полными данными
                histories_out = await self._build_histories_out(ordered_histories, user_id)
                
                return FavoritesResponse(
                    history_ids=history_ids,
                    histories=histories_out,
                    total=total,
                    skip=skip,
                    limit=limit
                )
                
        except Exception as e:
            app_logger.exception(f"Ошибка при получении избранных пользователя {user_id}: {e}")
            raise DatabaseError(f"Ошибка при получении избранных")

    async def _build_histories_out(self, histories: List[History], me_user_id: int) -> List[HistoryOut]:
        """Построить список HistoryOut с полными данными"""
        from database.managers.history_manager import HistoryManager
        
        history_manager = HistoryManager()
        return await history_manager._build_histories_with_counts(
            histories=histories,
            schema_class=HistoryOut,
            me_user_id=me_user_id
        )

