from typing import List
from sqlalchemy import select

from database.managers.base_file_manager import BaseFileManager
from database.managers.session_manager import manager
from database.models.private_media_file import PrivateMediaFile
from database.models.message import Message

from schemas.private_media import PrivateMediaFileUpdate

from core.logger import app_logger

class PrivateMediaFileManager(BaseFileManager[PrivateMediaFile, PrivateMediaFileUpdate]):
    def __init__(self):
        super().__init__(PrivateMediaFile)
    
    def _get_additional_file_fields(self, file_data: dict) -> dict:
        return {
            'message_id': file_data.get('message_id')
        }

    async def create_private_file(self, file_data: dict) -> PrivateMediaFile:
        """Создать приватный медиафайл"""
        async with manager.get_async_session() as session:
            try:
                file_obj = PrivateMediaFile(
                    filename=file_data['filename'],
                    file_key=file_data['file_key'],
                    file_type=file_data['file_type'],
                    mime_type=file_data['mime_type'],
                    file_size=file_data['file_size'],
                    folder=file_data['folder'],
                    **self._get_additional_file_fields(file_data)
                )
                
                session.add(file_obj)
                await session.commit()
                await session.refresh(file_obj)
                
                app_logger.info(f"Приватный файл создан: {file_obj.file_key}")
                return file_obj
                
            except Exception as e:
                await session.rollback()
                app_logger.error(f"Ошибка создания приватного файла: {e}")
                raise


    async def get_by_message_id(self, message_id: int) -> List[PrivateMediaFile]:
        return await self.get_files_by_entity_id('message_id', message_id)

    async def get_voice_messages(self, limit: int = 50, offset: int = 0) -> List[PrivateMediaFile]:
        async with manager.get_async_session() as session:
            try:
                query = (
                    select(PrivateMediaFile)
                    .where(PrivateMediaFile.file_type == 'voice')
                    .order_by(PrivateMediaFile.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                app_logger.error(f"Ошибка получения голосовых сообщений: {e}")
                return []

    async def get_video_messages(self, limit: int = 50, offset: int = 0) -> List[PrivateMediaFile]:
        async with manager.get_async_session() as session:
            try:
                query = (
                    select(PrivateMediaFile)
                    .where(PrivateMediaFile.file_type == 'video')
                    .order_by(PrivateMediaFile.created_at.desc())
                    .offset(offset)
                    .limit(limit)
                )
                
                result = await session.execute(query)
                return result.scalars().all()
                
            except Exception as e:
                app_logger.error(f"Ошибка получения видео сообщений: {e}")
                return []

    async def attach_to_message(self, file_id: int, message_id: int) -> bool:
        async with manager.get_async_session() as session:
            try:
                private_file = await session.get(PrivateMediaFile, file_id)
                if not private_file:
                    return False

                message = await session.get(Message, message_id)
                if not message:
                    return False

                if await self.attach_file_to_entity(file_id, 'message_id', message_id):
                    await session.commit()
                    return True
                return False
                
            except Exception as e:
                await session.rollback()
                app_logger.error(f"Ошибка прикрепления файла {file_id} к сообщению {message_id}: {e}")
                return False

    async def detach_from_message(self, file_id: int) -> bool:
        async with manager.get_async_session() as session:
            try:
                private_file = await session.get(PrivateMediaFile, file_id)
                if not private_file:
                    return False

                if await self.detach_file_from_entity(file_id, 'message_id'):
                    await session.commit()
                    return True
                return False
                
            except Exception as e:
                await session.rollback()
                app_logger.error(f"Ошибка открепления файла {file_id}: {e}")
                return False

