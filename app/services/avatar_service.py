from typing import Optional

from fastapi import HTTPException 
from fastapi import UploadFile
from fastapi import status

from core.logger import app_logger
from database.managers.user_manager import UserManager
from database.models.user import User
from services.file_validation_service import FileValidationService
from services.s3_service import S3Service

class AvatarService:
    def __init__(self):
        self.user_manager = UserManager()
        self.s3_service = S3Service()
    
    async def get_user_avatar_url(self, user_id: int) -> str:
        user = await self.user_manager.get_obj_by_id(user_id)
        
        if not user.avatar_key:
            app_logger.info(f"User {user_id} has no avatar")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="У пользователя нет аватара"
            )
        
        presigned_url = await self.s3_service.generate_presigned_url(user.avatar_key)
        app_logger.info(f"Generated avatar URL for user {user_id}")
        
        return presigned_url
    
    async def get_my_avatar_url(self, current_user: User) -> str:
        if not current_user.avatar_key:
            app_logger.info(f"User {current_user.id} has no avatar")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="У вас нет аватара"
            )
        
        presigned_url = await self.s3_service.generate_presigned_url(current_user.avatar_key)
        app_logger.info(f"Generated avatar URL for current user {current_user.id}")
        
        return presigned_url
    
    async def upload_my_avatar(self, file: UploadFile, current_user: User) -> tuple[str, str]:
        await FileValidationService.validate_avatar_file(file)
        
        file_content = await file.read()
        
        object_key = await self.s3_service.upload_file(
            file=file_content,
            filename=file.filename or "avatar",
            folder="avatars"
        )
        
        await self._delete_old_avatar(current_user.avatar_key)
        await self.user_manager.update_user_avatar(current_user.id, object_key)
        
        presigned_url = await self.s3_service.generate_presigned_url(object_key)
        
        app_logger.info(f"Avatar uploaded for user {current_user.id}: {object_key}")
        return object_key, presigned_url
    
    async def get_avatar_url_or_none(self, user: User) -> str | None:
        """Получить URL аватара пользователя или None, если аватара нет"""
        if not user.avatar_key:
            return None
        
        try:
            presigned_url = await self.s3_service.generate_presigned_url(user.avatar_key)
            return presigned_url
        except Exception as e:
            app_logger.warning(f"Failed to generate avatar URL for user {user.id}: {e}")
            return None

    async def _delete_old_avatar(self, old_avatar_key: Optional[str]) -> None:
        if not old_avatar_key:
            return
        
        try:
            await self.s3_service.delete_file(old_avatar_key)
            app_logger.info(f"Deleted old avatar: {old_avatar_key}")
        except Exception as e:
            app_logger.warning(f"Failed to delete old avatar {old_avatar_key}: {e}")


avatar_service = AvatarService()
