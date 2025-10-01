"""Базовый менеджер для файловых операций.

Содержит повторно используемую логику для работы с медиафайлами:
- создание файлов
- получение по различным критериям
- подсчет файлов
- прикрепление/открепление файлов
"""
from abc import ABC
from typing import List, Optional, Type, TypeVar, Generic
from sqlalchemy import select, and_, func
from sqlalchemy.future import select
from sqlalchemy.orm import joinedload

from database.managers.base_manager import BaseManager
from database.managers.session_manager import manager
from core.logger import app_logger

TFileModel = TypeVar('TFileModel')
TUpdateSchema = TypeVar('TUpdateSchema')

class BaseFileManager(BaseManager[TFileModel, TUpdateSchema], ABC, Generic[TFileModel, TUpdateSchema]):
    """Базовый класс для файловых менеджеров с общей логикой."""
    
    def __init__(self, model: Type[TFileModel]):
        super().__init__(model)
    
    async def create_file(self, file_data: dict, user_id: int) -> TFileModel:
        """Создать файл с базовыми данными."""
        async with manager.get_async_session() as session:
            try:
                file_obj = self._model(
                    filename=file_data['filename'],
                    file_key=file_data['file_key'],
                    file_type=file_data['file_type'],
                    mime_type=file_data['mime_type'],
                    file_size=file_data['file_size'],
                    folder=file_data['folder'],
                    user_id=user_id,
                    **self._get_additional_file_fields(file_data)
                )
                
                session.add(file_obj)
                await session.commit()
                await session.refresh(file_obj)
                
                app_logger.info(f"Файл создан: {file_obj.file_key} пользователем {user_id}")
                return file_obj
                
            except Exception as e:
                await session.rollback()
                app_logger.error(f"Ошибка создания файла: {e}")
                raise
    
    def _get_additional_file_fields(self, file_data: dict) -> dict:
        """Получить дополнительные поля для конкретной модели файла.
        
        Переопределяется в наследниках для добавления специфичных полей.
        """
        return {}
    
    async def get_by_user_id(self, user_id: int, limit: int = 50, offset: int = 0) -> List[TFileModel]:
        """Получить файлы пользователя."""
        async with manager.get_async_session() as session:
            try:
                query = (
                    select(self._model)
                    .where(self._model.user_id == user_id)
                    .order_by(self._model.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                app_logger.error(f"Ошибка получения файлов пользователя {user_id}: {e}")
                return []
    
    async def get_by_file_type(self, user_id: int, file_type: str, limit: int = 50, offset: int = 0) -> List[TFileModel]:
        """Получить файлы пользователя по типу."""
        async with manager.get_async_session() as session:
            try:
                query = (
                    select(self._model)
                    .where(
                        and_(
                            self._model.user_id == user_id,
                            self._model.file_type == file_type
                        )
                    )
                    .order_by(self._model.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                app_logger.error(f"Ошибка получения файлов типа {file_type} пользователя {user_id}: {e}")
                return []
    
    async def get_by_file_key(self, file_key: str) -> Optional[TFileModel]:
        """Получить файл по ключу."""
        async with manager.get_async_session() as session:
            try:
                query = select(self._model).where(self._model.file_key == file_key)
                result = await session.execute(query)
                return result.scalar_one_or_none()
                
            except Exception as e:
                app_logger.error(f"Ошибка получения файла по ключу {file_key}: {e}")
                return None
    
    async def count_by_user_id(self, user_id: int) -> int:
        """Подсчитать количество файлов пользователя."""
        async with manager.get_async_session() as session:
            try:
                query = select(func.count(self._model.id)).where(self._model.user_id == user_id)
                result = await session.execute(query)
                return result.scalar() or 0
                
            except Exception as e:
                app_logger.error(f"Ошибка подсчета файлов пользователя {user_id}: {e}")
                return 0
    
    async def attach_file_to_entity(self, file_id: int, entity_field: str, entity_id: int) -> bool:
        """Прикрепить файл к сущности (history, comment, message и т.д.)."""
        async with manager.get_async_session() as session:
            try:
                file_obj = await session.get(self._model, file_id)
                if not file_obj:
                    return False
                
                setattr(file_obj, entity_field, entity_id)
                await session.commit()
                return True
                
            except Exception as e:
                await session.rollback()
                app_logger.error(f"Ошибка прикрепления файла {file_id} к {entity_field} {entity_id}: {e}")
                return False
    
    async def detach_file_from_entity(self, file_id: int, entity_field: str) -> bool:
        """Открепить файл от сущности."""
        async with manager.get_async_session() as session:
            try:
                file_obj = await session.get(self._model, file_id)
                if not file_obj:
                    return False
                
                setattr(file_obj, entity_field, None)
                await session.commit()
                return True
                
            except Exception as e:
                await session.rollback()
                app_logger.error(f"Ошибка открепления файла {file_id} от {entity_field}: {e}")
                return False
    
    async def get_files_by_entity_id(self, entity_field: str, entity_id: int, limit: int = 50, offset: int = 0) -> List[TFileModel]:
        """Получить файлы по ID сущности."""
        async with manager.get_async_session() as session:
            try:
                query = (
                    select(self._model)
                    .where(getattr(self._model, entity_field) == entity_id)
                    .order_by(self._model.created_at.asc())
                    .offset(offset)
                    .limit(limit)
                )
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                app_logger.error(f"Ошибка получения файлов по {entity_field} {entity_id}: {e}")
                return []
    
    async def count_by_entity_id(self, entity_field: str, entity_id: int) -> int:
        """Подсчитать количество файлов по ID сущности."""
        async with manager.get_async_session() as session:
            try:
                query = select(func.count(self._model.id)).where(getattr(self._model, entity_field) == entity_id)
                result = await session.execute(query)
                return result.scalar() or 0
                
            except Exception as e:
                app_logger.error(f"Ошибка подсчета файлов по {entity_field} {entity_id}: {e}")
                return 0
