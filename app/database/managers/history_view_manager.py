from __future__ import annotations

from typing import List
from typing import Sequence

from core.logger import app_logger

from database.managers.base_manager import BaseManager

from database.models.history import History
from database.models.history_view import HistoryView

from exceptions.base import DatabaseError

from schemas.history import HistoryOut
from schemas.history_view import HistoryViewCreate
from schemas.history_view import HistoryViewsBulkCreate
from schemas.history_view import HistoryViewOut
from schemas.history_view import HistoryViewWithHistoryOut
from schemas.history_view import HistoryViewWithUserOut

from sqlalchemy import desc
from sqlalchemy import func
from sqlalchemy import text
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError

class HistoryViewManager(BaseManager[HistoryView, None]):
    def __init__(self) -> None:
        super().__init__(HistoryView)

    async def add_view(self, user_id: int, history_id: int) -> HistoryViewOut | None:
        try:
            existing_view = await self.get_view_by_user_and_history(user_id, history_id)
            if existing_view:
                return None
            
            async with self.manager.get_async_session() as session:
                # Создаем просмотр
                view_data = HistoryViewCreate(history_id=history_id)
                view = HistoryView(**view_data.model_dump(), user_id=user_id)
                session.add(view)
                await session.flush()  # Получаем ID без коммита
                
                # Увеличиваем счетчик просмотров
                from sqlalchemy import text
                await session.execute(
                    text("UPDATE histories SET views = views + 1 WHERE id = :history_id"),
                    {"history_id": history_id}
                )
                
                await session.commit()
                
                app_logger.info_event(
                    "history_view_added", 
                    user_id=user_id, 
                    history_id=history_id,
                    view_id=view.id
                )
                
                return HistoryViewOut.model_validate(view)
            
        except IntegrityError as e:
            app_logger.warning_event(
                "history_view_already_exists",
                user_id=user_id,
                history_id=history_id,
                error=str(e)
            )
            return None
        except Exception as e:
            app_logger.error_event(
                "history_view_add_error",
                user_id=user_id,
                history_id=history_id,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при добавлении просмотра: {str(e)}")

    async def add_views_bulk(self, user_id: int, history_ids: List[int]) -> List[HistoryViewOut]:
        """Добавляет просмотры для списка историй одним запросом."""
        try:
            if not history_ids:
                return []
            
            async with self.manager.get_async_session() as session:
                # Получаем уже существующие просмотры
                existing_views_query = select(HistoryView.history_id).where(
                    HistoryView.user_id == user_id,
                    HistoryView.history_id.in_(history_ids)
                )
                existing_result = await session.execute(existing_views_query)
                existing_history_ids = {row[0] for row in existing_result.all()}
                
                # Определяем новые истории для просмотра
                new_history_ids = [hid for hid in history_ids if hid not in existing_history_ids]
                
                if not new_history_ids:
                    # Все просмотры уже существуют, возвращаем существующие
                    existing_views_query = select(HistoryView).where(
                        HistoryView.user_id == user_id,
                        HistoryView.history_id.in_(history_ids)
                    )
                    existing_views_result = await session.execute(existing_views_query)
                    existing_views = existing_views_result.scalars().all()
                    return [HistoryViewOut.model_validate(view) for view in existing_views]
                
                # Создаем новые просмотры
                new_views = []
                for history_id in new_history_ids:
                    view = HistoryView(user_id=user_id, history_id=history_id)
                    session.add(view)
                    new_views.append(view)
                
                await session.flush()  # Получаем ID без коммита
                
                # Обновляем счетчики просмотров для всех новых историй одним запросом
                if new_history_ids:
                    from sqlalchemy import update
                    await session.execute(
                        update(History)
                        .where(History.id.in_(new_history_ids))
                        .values(views=History.views + 1)
                    )
                
                await session.commit()
                
                app_logger.info_event(
                    "history_views_bulk_added",
                    user_id=user_id,
                    history_ids=new_history_ids,
                    count=len(new_views)
                )
                
                # Возвращаем все просмотры (новые + существующие)
                all_views_query = select(HistoryView).where(
                    HistoryView.user_id == user_id,
                    HistoryView.history_id.in_(history_ids)
                )
                all_views_result = await session.execute(all_views_query)
                all_views = all_views_result.scalars().all()
                
                return [HistoryViewOut.model_validate(view) for view in all_views]
                
        except Exception as e:
            app_logger.error_event(
                "history_views_bulk_add_error",
                user_id=user_id,
                history_ids=history_ids,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при массовом добавлении просмотров: {str(e)}")

    async def get_view_by_user_and_history(self, user_id: int, history_id: int) -> HistoryViewOut | None:
        try:
            async with self.manager.get_async_session() as session:
                query = select(HistoryView).where(
                    HistoryView.user_id == user_id,
                    HistoryView.history_id == history_id
                )
                
                result = await session.execute(query)
                view = result.scalar_one_or_none()
                
                if view:
                    return HistoryViewOut.model_validate(view)
                return None
                
        except Exception as e:
            app_logger.error_event(
                "history_view_get_error",
                user_id=user_id,
                history_id=history_id,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при получении просмотра: {str(e)}")

    async def get_user_views(self, user_id: int, skip: int = 0, limit: int = 50) -> Sequence[HistoryViewWithHistoryOut]:
        try:
            async with self.manager.get_async_session() as session:
                query = (
                    select(HistoryView)
                    .options(joinedload(HistoryView.history).joinedload(History.author))
                    .where(HistoryView.user_id == user_id)
                    .order_by(desc(HistoryView.viewed_at))
                    .offset(skip)
                    .limit(limit)
                )
                
                result = await session.execute(query)
                views = result.unique().scalars().all()
                
                # Получаем количество просмотров для всех историй из таблицы histories
                history_ids = [view.history.id for view in views]
                views_count_map = {}
                if history_ids:
                    views_count_query = select(History.id, History.views).where(
                        History.id.in_(history_ids)
                    )
                    views_count_result = await session.execute(views_count_query)
                    views_count_map = {hid: int(views) for hid, views in views_count_result.all()}
                
                views_with_histories = []
                for view in views:
                    # Создаем HistoryOut из связанной истории
                    history_out = await HistoryOut.from_model_with_counts(
                        history_obj=view.history,
                        likes=view.history.likes,
                        dislikes=view.history.dislikes,
                        comments=view.history.comments,
                        views=views_count_map.get(view.history.id, 0)
                    )
                    
                    views_with_histories.append(HistoryViewWithHistoryOut(
                        id=view.id,
                        user_id=view.user_id,
                        history=history_out,
                        viewed_at=view.viewed_at
                    ))
                
                return views_with_histories
                
        except Exception as e:
            app_logger.error_event(
                "user_views_get_error",
                user_id=user_id,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при получении просмотров пользователя: {str(e)}")

    async def get_history_views(self, history_id: int, skip: int = 0, limit: int = 50) -> Sequence[HistoryViewWithUserOut]:
        try:
            async with self.manager.get_async_session() as session:
                query = (
                    select(HistoryView)
                    .options(joinedload(HistoryView.user))
                    .where(HistoryView.history_id == history_id)
                    .order_by(desc(HistoryView.viewed_at))
                    .offset(skip)
                    .limit(limit)
                )
                
                result = await session.execute(query)
                views = result.unique().scalars().all()
                
                views_with_users = []
                for view in views:
                    from schemas.user import UserShortOut
                    
                    views_with_users.append(HistoryViewWithUserOut(
                        id=view.id,
                        history_id=view.history_id,
                        user=UserShortOut.model_validate(view.user),
                        viewed_at=view.viewed_at
                    ))
                
                return views_with_users
                
        except Exception as e:
            app_logger.error_event(
                "history_views_get_error",
                history_id=history_id,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при получении просмотров истории: {str(e)}")

    async def get_views_count_by_history(self, history_id: int) -> int:
        try:
            async with self.manager.get_async_session() as session:
                query = select(func.count(HistoryView.id)).where(HistoryView.history_id == history_id)
                result = await session.execute(query)
                return result.scalar() or 0
                
        except Exception as e:
            app_logger.error_event(
                "views_count_get_error",
                history_id=history_id,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при получении количества просмотров: {str(e)}")

    async def get_views_count_by_user(self, user_id: int) -> int:
        try:
            async with self.manager.get_async_session() as session:
                query = select(func.count(HistoryView.id)).where(HistoryView.user_id == user_id)
                result = await session.execute(query)
                return result.scalar() or 0
                
        except Exception as e:
            app_logger.error_event(
                "user_views_count_get_error",
                user_id=user_id,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при получении количества просмотров пользователя: {str(e)}")

    async def _increment_history_views(self, history_id: int) -> None:
        try:
            async with self.manager.get_async_session() as session:
                from sqlalchemy import text
                # Увеличиваем счетчик просмотров в таблице histories
                await session.execute(
                    text("UPDATE histories SET views_count = views_count + 1 WHERE id = :history_id"),
                    {"history_id": history_id}
                )
                await session.commit()
                    
        except Exception as e:
            app_logger.error_event(
                "history_views_increment_error",
                history_id=history_id,
                error=str(e)
            )
            raise DatabaseError(f"Ошибка при увеличении счетчика просмотров: {str(e)}")
