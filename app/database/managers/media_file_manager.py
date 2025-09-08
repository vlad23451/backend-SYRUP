from typing import List

from sqlalchemy import select 
from sqlalchemy import and_
from sqlalchemy import desc

from database.managers.base_manager import BaseManager
from database.models.media_file import MediaFile
from schemas.media import MediaFileUpdate

class MediaFileManager(BaseManager[MediaFile, MediaFileUpdate]):
    def __init__(self):
        super().__init__(MediaFile)
    
    async def get_by_user_id(self, user_id: int, limit: int = 50, offset: int = 0) -> List[MediaFile]:
        async with self.manager.get_async_session() as session:
            stmt = select(MediaFile).where(
                MediaFile.user_id == user_id
            ).order_by(desc(MediaFile.created_at)).limit(limit).offset(offset)
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_by_history_id(self, history_id: int) -> List[MediaFile]:
        async with self.manager.get_async_session() as session:
            stmt = select(MediaFile).where(
                MediaFile.history_id == history_id
            ).order_by(MediaFile.created_at)
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_by_file_type(self,
                               user_id: int,
                               file_type: str,
                               limit: int = 50,
                               offset: int = 0) -> List[MediaFile]:
        async with self.manager.get_async_session() as session:
            stmt = select(MediaFile).where(
                and_(
                    MediaFile.user_id == user_id,
                    MediaFile.file_type == file_type
                )
            ).order_by(desc(MediaFile.created_at)).limit(limit).offset(offset)
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def get_public_files(self, limit: int = 50, offset: int = 0) -> List[MediaFile]:
        async with self.manager.get_async_session() as session:
            stmt = select(MediaFile).where(
                MediaFile.is_public == True
            ).order_by(desc(MediaFile.created_at)).limit(limit).offset(offset)
            
            result = await session.execute(stmt)
            return result.scalars().all()
    
    async def count_by_user_id(self, user_id: int) -> int:
        async with self.manager.get_async_session() as session:
            stmt = select(MediaFile).where(MediaFile.user_id == user_id)
            result = await session.execute(stmt)
            return len(result.scalars().all())
    
    async def count_by_history_id(self, history_id: int) -> int:
        async with self.manager.get_async_session() as session:
            stmt = select(MediaFile).where(MediaFile.history_id == history_id)
            result = await session.execute(stmt)
            return len(result.scalars().all())
    
    async def count_public_files(self) -> int:
        async with self.manager.get_async_session() as session:
            stmt = select(MediaFile).where(MediaFile.is_public == True)
            result = await session.execute(stmt)
            return len(result.scalars().all())
    
    async def attach_to_history(self, file_id: int, history_id: int) -> bool:
        async with self.manager.get_async_session() as session:
            try:
                file = await self.get_obj_by_id(file_id)
                if not file:
                    return False
                
                file.history_id = history_id
                session.add(file)
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                return False
    
    async def detach_from_history(self, file_id: int, history_id: int) -> bool:
        async with self.manager.get_async_session() as session:
            try:
                file = await self.get_obj_by_id(file_id)
                if not file or file.history_id != history_id:
                    return False
                
                file.history_id = None
                session.add(file)
                await session.commit()
                return True
            except Exception:
                await session.rollback()
                return False
    
    async def get_by_file_key(self, file_key: str) -> MediaFile | None:
        async with self.manager.get_async_session() as session:
            stmt = select(MediaFile).where(MediaFile.file_key == file_key)
            result = await session.execute(stmt)
            return result.scalar_one_or_none()
