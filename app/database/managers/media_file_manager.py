from typing import List

from sqlalchemy import select 
from sqlalchemy import desc

from database.managers.base_file_manager import BaseFileManager
from database.models.media_file import MediaFile
from schemas.media import MediaFileUpdate

class MediaFileManager(BaseFileManager[MediaFile, MediaFileUpdate]):
    def __init__(self):
        super().__init__(MediaFile)
    
    def _get_additional_file_fields(self, file_data: dict) -> dict:
        return {
            'history_id': file_data.get('history_id'),
            'comment_id': file_data.get('comment_id'),
            'is_public': file_data.get('is_public', False),
            'description': file_data.get('description')
        }
    
    async def get_by_history_id(self, history_id: int) -> List[MediaFile]:
        return await self.get_files_by_entity_id('history_id', history_id)
    
    async def get_by_comment_id(self, comment_id: int) -> List[MediaFile]:
        return await self.get_files_by_entity_id('comment_id', comment_id)
    
    async def get_by_comment_ids(self, comment_ids: List[int]) -> List[MediaFile]:
        async with self.manager.get_async_session() as session:
            stmt = select(MediaFile).where(
                MediaFile.comment_id.in_(comment_ids)
            ).order_by(MediaFile.comment_id, MediaFile.created_at)
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_public_files(self, limit: int = 50, offset: int = 0) -> List[MediaFile]:
        async with self.manager.get_async_session() as session:
            stmt = select(MediaFile).where(
                MediaFile.is_public == True
            ).order_by(desc(MediaFile.created_at)).limit(limit).offset(offset)
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def count_by_history_id(self, history_id: int) -> int:
        return await self.count_by_entity_id('history_id', history_id)
    
    async def count_public_files(self) -> int:
        async with self.manager.get_async_session() as session:
            stmt = select(MediaFile).where(MediaFile.is_public == True)
            result = await session.execute(stmt)
            return len(result.scalars().all())
    
    async def attach_to_history(self, file_id: int, history_id: int) -> bool:
        return await self.attach_file_to_entity(file_id, 'history_id', history_id)
    
    async def attach_to_comment(self, file_id: int, comment_id: int) -> bool:
        return await self.attach_file_to_entity(file_id, 'comment_id', comment_id)
    
    async def detach_from_history(self, file_id: int, history_id: int) -> bool:
        file_obj = await self.get_obj_by_id(file_id)
        if not file_obj or file_obj.history_id != history_id:
            return False
        return await self.detach_file_from_entity(file_id, 'history_id')
    
    async def detach_from_comment(self, file_id: int, comment_id: int) -> bool:
        file_obj = await self.get_obj_by_id(file_id)
        if not file_obj or file_obj.comment_id != comment_id:
            return False
        return await self.detach_file_from_entity(file_id, 'comment_id')
