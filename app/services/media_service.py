import mimetypes
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import UploadFile

from database.managers.media_file_manager import MediaFileManager
from database.models.media_file import MediaFile
from services.s3_service import S3Service
from core.logger import app_logger

from exceptions.media_files import MediaFileValidationError
from exceptions.media_files import MediaFileTypeNotSupportedError
from exceptions.media_files import MediaFileSizeExceededError
from exceptions.media_files import MediaFileUploadError
from exceptions.media_files import MediaFileOperationError

class MediaService:
    def __init__(self, media_file_manager: MediaFileManager):
        self.media_file_manager = media_file_manager
        self.s3_service = S3Service()
        
        self.file_type_config = {
            'image': {
                'folder': 'photos',
                'allowed_extensions': ['.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp'],
                'max_size_mb': 10
            },
            'video': {
                'folder': 'videos',
                'allowed_extensions': ['.mp4', '.avi', '.mov', '.wmv', '.flv', '.webm', '.mkv'],
                'max_size_mb': 100
            },
            'audio': {
                'folder': 'audio',
                'allowed_extensions': ['.mp3', '.wav', '.ogg', '.flac', '.aac', '.m4a'],
                'max_size_mb': 50
            },
            'document': {
                'folder': 'documents',
                'allowed_extensions': ['.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt'],
                'max_size_mb': 20
            }
        }
    
    def _get_file_type(self, filename: str, mime_type: str) -> str:
        extension = Path(filename).suffix.lower()
        
        if extension in self.file_type_config['image']['allowed_extensions']:
            return 'image'
        elif extension in self.file_type_config['video']['allowed_extensions']:
            return 'video'
        elif extension in self.file_type_config['audio']['allowed_extensions']:
            return 'audio'
        elif extension in self.file_type_config['document']['allowed_extensions']:
            return 'document'
        
        if mime_type.startswith('image/'):
            return 'image'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('audio/'):
            return 'audio'
        elif mime_type.startswith('application/') or mime_type.startswith('text/'):
            return 'document'
        
        return 'document'
    
    def _validate_file(self, file: UploadFile, file_type: str) -> None:
        if file_type not in self.file_type_config:
            raise MediaFileTypeNotSupportedError(f"Неподдерживаемый тип файла: {file_type}")
        
        config = self.file_type_config[file_type]
        extension = Path(file.filename).suffix.lower()
        
        if extension not in config['allowed_extensions']:
            raise MediaFileValidationError(f"Неподдерживаемое расширение файла: {extension}")

        if hasattr(file, 'size') and file.size:
            max_size_bytes = config['max_size_mb'] * 1024 * 1024
            if file.size > max_size_bytes:
                raise MediaFileSizeExceededError(f"Файл слишком большой. Максимальный размер: {config['max_size_mb']}MB")
    
    async def upload_file(self, file: UploadFile, user_id: int, description: Optional[str] = None, is_public: bool = False) -> Dict[str, Any]:
        try:
            mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or 'application/octet-stream'

            file_type = self._get_file_type(file.filename, mime_type)

            self._validate_file(file, file_type)

            config = self.file_type_config[file_type]
            folder = config['folder']

            file_content = await file.read()

            file_size = len(file_content)
            max_size_bytes = config['max_size_mb'] * 1024 * 1024
            if file_size > max_size_bytes:
                raise MediaFileSizeExceededError(f"Файл слишком большой. Максимальный размер: {config['max_size_mb']}MB")

            file_key = await self.s3_service.upload_file(
                file=file_content,
                filename=file.filename,
                folder=folder
            )

            media_file = MediaFile(
                filename=file.filename,
                file_key=file_key,
                file_type=file_type,
                mime_type=mime_type,
                file_size=file_size,
                folder=folder,
                user_id=user_id,
                description=description,
                is_public=is_public
            )
            
            await self.media_file_manager.create_obj(media_file)

            download_url = await self.s3_service.generate_presigned_url(file_key)
            
            app_logger.info(f"Файл загружен: {file_key} пользователем {user_id}")
            
            return {
                'id': media_file.id,
                'filename': media_file.filename,
                'file_key': media_file.file_key,
                'file_type': media_file.file_type,
                'mime_type': media_file.mime_type,
                'file_size': media_file.file_size,
                'folder': media_file.folder,
                'download_url': download_url,
                'created_at': media_file.created_at
            }
            
        except (MediaFileValidationError, MediaFileTypeNotSupportedError, MediaFileSizeExceededError):
            raise
        except Exception as e:
            app_logger.error(f"Ошибка загрузки файла: {e}")
            raise MediaFileUploadError("Ошибка загрузки файла")
    
    async def get_file(self, file_id: int, user_id: int) -> Optional[Dict[str, Any]]:
        try:
            media_file = await self.media_file_manager.get_obj_by_id(file_id)
            
            if not media_file:
                return None

            if media_file.user_id != user_id and not media_file.is_public:
                return None

            download_url = await self.s3_service.generate_presigned_url(media_file.file_key)
            
            return {
                'id': media_file.id,
                'filename': media_file.filename,
                'file_key': media_file.file_key,
                'file_type': media_file.file_type,
                'mime_type': media_file.mime_type,
                'file_size': media_file.file_size,
                'folder': media_file.folder,
                'user_id': media_file.user_id,
                'history_id': media_file.history_id,
                'description': media_file.description,
                'is_public': media_file.is_public,
                'download_url': download_url,
                'created_at': media_file.created_at,
                'updated_at': media_file.updated_at
            }
            
        except Exception as e:
            app_logger.error(f"Ошибка получения файла {file_id}: {e}")
            return None
    
    async def get_user_files(self,
                             user_id: int,
                             file_type: str | None = None,
                             limit: int = 50,
                             offset: int = 0) -> List[Dict[str, Any]]:
        try:
            if file_type:
                media_files = await self.media_file_manager.get_by_file_type(user_id, file_type, limit, offset)
            else:
                media_files = await self.media_file_manager.get_by_user_id(user_id, limit, offset)
            
            result = []
            for media_file in media_files:
                download_url = await self.s3_service.generate_presigned_url(media_file.file_key)
                result.append({
                    'id': media_file.id,
                    'filename': media_file.filename,
                    'file_key': media_file.file_key,
                    'file_type': media_file.file_type,
                    'mime_type': media_file.mime_type,
                    'file_size': media_file.file_size,
                    'folder': media_file.folder,
                    'history_id': media_file.history_id,
                    'description': media_file.description,
                    'is_public': media_file.is_public,
                    'download_url': download_url,
                    'created_at': media_file.created_at,
                    'updated_at': media_file.updated_at
                })
            
            return result
            
        except Exception as e:
            app_logger.error(f"Ошибка получения файлов пользователя {user_id}: {e}")
            return []
    
    async def get_history_files(self, history_id: int) -> List[Dict[str, Any]]:
        try:
            media_files = await self.media_file_manager.get_by_history_id(history_id)
            
            result = []
            for media_file in media_files:
                download_url = await self.s3_service.generate_presigned_url(media_file.file_key)
                result.append({
                    'id': media_file.id,
                    'filename': media_file.filename,
                    'file_key': media_file.file_key,
                    'file_type': media_file.file_type,
                    'mime_type': media_file.mime_type,
                    'file_size': media_file.file_size,
                    'folder': media_file.folder,
                    'user_id': media_file.user_id,
                    'description': media_file.description,
                    'is_public': media_file.is_public,
                    'download_url': download_url,
                    'created_at': media_file.created_at,
                    'updated_at': media_file.updated_at
                })
            
            return result
            
        except Exception as e:
            app_logger.error(f"Ошибка получения файлов истории {history_id}: {e}")
            return []
    
    async def get_comment_files(self, comment_id: int) -> List[Dict[str, Any]]:
        try:
            media_files = await self.media_file_manager.get_by_comment_id(comment_id)
            
            result = []
            for media_file in media_files:
                download_url = await self.s3_service.generate_presigned_url(media_file.file_key)
                result.append({
                    'id': media_file.id,
                    'filename': media_file.filename,
                    'file_key': media_file.file_key,
                    'file_type': media_file.file_type,
                    'mime_type': media_file.mime_type,
                    'file_size': media_file.file_size,
                    'folder': media_file.folder,
                    'user_id': media_file.user_id,
                    'comment_id': media_file.comment_id,
                    'description': media_file.description,
                    'is_public': media_file.is_public,
                    'download_url': download_url,
                    'created_at': media_file.created_at,
                    'updated_at': media_file.updated_at
                })
            
            return result
            
        except Exception as e:
            app_logger.error(f"Ошибка получения файлов комментария {comment_id}: {e}")
            return []
    
    async def get_comment_files_batch(self, comment_ids: List[int]) -> List[Dict[str, Any]]:
        """Получить файлы для списка комментариев одним запросом"""
        try:
            media_files = await self.media_file_manager.get_by_comment_ids(comment_ids)
            
            result = []
            for media_file in media_files:
                download_url = await self.s3_service.generate_presigned_url(media_file.file_key)
                result.append({
                    'id': media_file.id,
                    'filename': media_file.filename,
                    'file_key': media_file.file_key,
                    'file_type': media_file.file_type,
                    'mime_type': media_file.mime_type,
                    'file_size': media_file.file_size,
                    'folder': media_file.folder,
                    'user_id': media_file.user_id,
                    'comment_id': media_file.comment_id,
                    'description': media_file.description,
                    'is_public': media_file.is_public,
                    'download_url': download_url,
                    'created_at': media_file.created_at,
                    'updated_at': media_file.updated_at
                })
            
            return result
            
        except Exception as e:
            app_logger.error(f"Ошибка получения файлов для комментариев {comment_ids}: {e}")
            return []
    
    async def update_file(self,
                          file_id: int,
                          user_id: int,
                          description: str | None= None,
                          is_public: bool | None = None) -> bool:
        try:
            media_file = await self.media_file_manager.get_obj_by_id(file_id)
            
            if not media_file or media_file.user_id != user_id:
                return False
            
            update_data = {}
            if description is not None:
                update_data['description'] = description
            if is_public is not None:
                update_data['is_public'] = is_public
            
            from schemas.media import MediaFileUpdate
            update_obj = MediaFileUpdate(**update_data)
            await self.media_file_manager.update_obj(media_file.id, update_obj)
            return True
            
        except Exception as e:
            app_logger.error(f"Ошибка обновления файла {file_id}: {e}")
            return False
    
    async def delete_file(self, file_id: int, user_id: int) -> bool:
        try:
            media_file = await self.media_file_manager.get_obj_by_id(file_id)
            
            if not media_file or media_file.user_id != user_id:
                return False

            await self.s3_service.delete_file(media_file.file_key)

            await self.media_file_manager.delete_obj(media_file.id)
            
            app_logger.info(f"Файл удален: {media_file.file_key} пользователем {user_id}")
            return True
            
        except Exception as e:
            app_logger.error(f"Ошибка удаления файла {file_id}: {e}")
            return False
    
    async def attach_to_history(self, file_id: int, history_id: int, user_id: int) -> bool:
        try:
            media_file = await self.media_file_manager.get_obj_by_id(file_id)
            
            if not media_file or media_file.user_id != user_id:
                return False
            
            return await self.media_file_manager.attach_to_history(file_id, history_id)
            
        except Exception as e:
            app_logger.error(f"Ошибка прикрепления файла {file_id} к истории {history_id}: {e}")
            return False
    
    async def attach_file(self, file_id: int, history_id: int | None = None, comment_id: int | None = None, user_id: int = None) -> bool:
        try:
            media_file = await self.media_file_manager.get_obj_by_id(file_id)
            
            if not media_file or media_file.user_id != user_id:
                return False
            
            if history_id:
                return await self.media_file_manager.attach_to_history(file_id, history_id)
            elif comment_id:
                return await self.media_file_manager.attach_to_comment(file_id, comment_id)
            else:
                return False
                
        except Exception as e:
            target = f"истории {history_id}" if history_id else f"комментарию {comment_id}"
            app_logger.error(f"Ошибка прикрепления файла {file_id} к {target}: {e}")
            return False
    
    async def detach_from_history(self, file_id: int, history_id: int, user_id: int) -> bool:
        try:
            media_file = await self.media_file_manager.get_obj_by_id(file_id)
            
            if not media_file or media_file.user_id != user_id:
                return False
            
            return await self.media_file_manager.detach_from_history(file_id, history_id)
            
        except Exception as e:
            app_logger.error(f"Ошибка открепления файла {file_id} от истории {history_id}: {e}")
            return False
    
    async def attach_to_comment(self, file_id: int, comment_id: int, user_id: int) -> bool:
        try:
            media_file = await self.media_file_manager.get_obj_by_id(file_id)
            
            if not media_file or media_file.user_id != user_id:
                return False
            
            return await self.media_file_manager.attach_to_comment(file_id, comment_id)
            
        except Exception as e:
            app_logger.error(f"Ошибка прикрепления файла {file_id} к комментарию {comment_id}: {e}")
            return False
    
    async def detach_from_comment(self, file_id: int, comment_id: int, user_id: int) -> bool:
        try:
            media_file = await self.media_file_manager.get_obj_by_id(file_id)
            
            if not media_file or media_file.user_id != user_id:
                return False
            
            return await self.media_file_manager.detach_from_comment(file_id, comment_id)
            
        except Exception as e:
            app_logger.error(f"Ошибка открепления файла {file_id} от комментария {comment_id}: {e}")
            return False
    
    async def detach_file(self, file_id: int, history_id: int | None = None, comment_id: int | None = None, user_id: int = None) -> bool:
        try:
            media_file = await self.media_file_manager.get_obj_by_id(file_id)
            
            if not media_file or media_file.user_id != user_id:
                return False
            
            if history_id:
                return await self.media_file_manager.detach_from_history(file_id, history_id)
            elif comment_id:
                return await self.media_file_manager.detach_from_comment(file_id, comment_id)
            else:
                return False
                
        except Exception as e:
            target = f"истории {history_id}" if history_id else f"комментарию {comment_id}"
            app_logger.error(f"Ошибка открепления файла {file_id} от {target}: {e}")
            return False
    
    async def get_public_files(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        try:
            files = await self.media_file_manager.get_public_files(limit, offset)
            total = await self.media_file_manager.count_public_files()
            
            result = []
            for media_file in files:
                download_url = await self.s3_service.generate_presigned_url(media_file.file_key)
                result.append({
                    'id': media_file.id,
                    'filename': media_file.filename,
                    'file_key': media_file.file_key,
                    'file_type': media_file.file_type,
                    'mime_type': media_file.mime_type,
                    'file_size': media_file.file_size,
                    'folder': media_file.folder,
                    'width': media_file.width,
                    'height': media_file.height,
                    'user_id': media_file.user_id,
                    'history_id': media_file.history_id,
                    'description': media_file.description,
                    'is_public': media_file.is_public,
                    'download_url': download_url,
                    'created_at': media_file.created_at,
                    'updated_at': media_file.updated_at
                })
            
            return {
                'files': result,
                'total': total,
                'page': offset // limit + 1,
                'per_page': limit
            }
            
        except Exception as e:
            app_logger.error(f"Ошибка получения публичных файлов: {e}")
            raise MediaFileOperationError("Ошибка получения публичных файлов")
