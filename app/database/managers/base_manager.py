"""Базовый менеджер CRUD-операций.

Содержит повторно используемую логику работы с async-сессиями SQLAlchemy,
обработку ошибок и общие операции (create/read/update/delete).
`BaseManager` типизирован: `TModel` — ORM-модель, `TUpdate` — pydantic-модель
обновления (partial update).
"""
from abc import ABC
from collections.abc import Sequence
from typing import List 
from typing import Type
from typing import TypeVar

from core.logger import app_logger
from database.managers.session_manager import Manager
from exceptions.base import DatabaseError
from exceptions.base import ModelNotFoundError

from pydantic import BaseModel
from sqlalchemy.future import select

TModel = TypeVar('TModel')
TUpdate = TypeVar('TUpdate', bound=BaseModel)

class BaseManager[TModel, TUpdate](ABC):
    """Общий менеджер для конкретных сущностей.

    Менеджер хранит ссылку на класс ORM-модели (`self._model`) и предоставляет
    стандартные методы для работы с сущностью. Потомки расширяют поведение
    специфическими выборками и агрегатами.
    """
    def __init__(self, model: Type[TModel]) -> None:
        self._model = model
        self.manager = Manager()

    async def create_obj(self, obj: TModel) -> TModel:
        """Создать объект в БД и вернуть его с присвоенным ID."""
        async with self.manager.get_async_session() as session:
            try:
                session.add(obj)
                await session.commit()
                await session.refresh(obj)
                return obj
            except Exception as e:
                await session.rollback()
                app_logger.exception(f"{self._model.__name__} не создан Traceback: {e}")
                raise DatabaseError()

    async def get_obj_by_id(self, id: int, options: List | None = None) -> TModel:
        """Получить объект по ID с опциональными ORM-опциями (joinedload и т.п.)."""
        if options is None:
            options = []
        try:
            async with self.manager.get_async_session() as session:
                query = select(self._model)
                for option in options:
                    query = query.options(option)
                result = await session.execute(
                    query.where(getattr(self._model, "id") == id)
                )
                obj = result.scalars().first()
                if not obj:
                    app_logger.error(f"{self._model.__name__} с id {id} не найден")
                    raise ModelNotFoundError(f"{self._model.__name__} с id {id} не найден")
                return obj
        except Exception as e:
            app_logger.exception(f"{self._model.__name__} с id {id} не найден Traceback: {e}")
            raise DatabaseError()

    async def get_all_obj(self,
                          options: List | None = None,
                          skip: int = 0,
                          limit: int = 100) -> Sequence[TModel]:
        """Получить список объектов с пагинацией и опциями подгрузки."""
        if options is None:
            options = []
        try:
            async with self.manager.get_async_session() as session:
                query = select(self._model)
                for option in options:
                    query = query.options(option)
                query = query.offset(skip).limit(limit)
                result = await session.execute(query)
                items = result.scalars().all()
                if not items:
                    app_logger.error(f"{self._model.__name__} не найдены")
                    raise ModelNotFoundError(f"{self._model.__name__} не найдены")
                return items
        except Exception as e:
            app_logger.exception(f"{self._model.__name__} не найдены Traceback: {e}")
            raise DatabaseError()

    async def update_obj(self, id: int, updated_obj: TUpdate) -> TModel:
        """Частично обновить объект по данным pydantic-схемы `updated_obj`."""
        async with self.manager.get_async_session() as session:
            try:
                obj = await session.get(self._model, int(id))
                if not obj:
                    app_logger.error(f"{self._model.__name__} с id {id} не найден: {e}")
                    raise ModelNotFoundError(f"{self._model.__name__} с id {id} не найден")
                data = updated_obj.model_dump(exclude_unset=True)
                for key, value in data.items():
                    if key != 'id':
                        setattr(obj, key, value)
                await session.commit()
                await session.refresh(obj)
                return obj
            except Exception as e:
                await session.rollback()
                app_logger.exception(f"{self._model.__name__} с id {id} не обновлен: {e}")
                raise DatabaseError()

    async def delete_obj(self, id: int) -> TModel:
        """Удалить объект по ID и вернуть удалённый экземпляр."""
        async with self.manager.get_async_session() as session:
            try:
                obj = await session.get(self._model, int(id))
                if not obj:
                    app_logger.error(f"{self._model.__name__} с id {id} не найден: {e}")
                    raise ModelNotFoundError(f"{self._model.__name__} с id {id} не найден")
                await session.delete(obj)
                await session.commit()
                return obj
            except Exception as e:
                await session.rollback()
                app_logger.exception(f"{self._model.__name__} с id {id} не удален: {e}")
                raise DatabaseError()
