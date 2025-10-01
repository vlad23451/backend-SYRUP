import mimetypes
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import UploadFile

from database.managers.private_media_file_manager import PrivateMediaFileManager
from database.models.private_media_file import PrivateMediaFile
from services.private_s3_service import PrivateS3Service
from core.logger import app_logger

from exceptions.media_files import MediaFileValidationError
from exceptions.media_files import MediaFileTypeNotSupportedError
from exceptions.media_files import MediaFileSizeExceededError
from exceptions.media_files import MediaFileUploadError

class PrivateMediaService:
    def __init__(self, private_media_file_manager: PrivateMediaFileManager):
        self.private_media_file_manager = private_media_file_manager
        self.private_s3_service = PrivateS3Service()
        
        # Конфигурация для приватных медиафайлов
        self.file_type_config = {
            'voice': {
                'folder': 'voice_messages',
                'allowed_extensions': ['.mp3', '.wav', '.ogg', '.m4a', '.aac'],
                'max_size_mb': 10,  # 10MB для голосовых сообщений
                'mime_types': ['audio/mpeg', 'audio/wav', 'audio/ogg', 'audio/mp4', 'audio/aac']
            },
            'video': {
                'folder': 'video_messages',
                'allowed_extensions': ['.mp4', '.webm', '.ogg', '.mov', '.avi'],
                'max_size_mb': 50,  # 50MB для видео сообщений
                'mime_types': ['video/mp4', 'video/webm', 'video/ogg', 'video/quicktime', 'video/x-msvideo']
            },
            'photo': {
                'folder': 'photo_messages',
                'allowed_extensions': ['.jpg', '.jpeg', '.png', '.gif', '.webp'],
                'max_size_mb': 5,  # 5MB для фото сообщений
                'mime_types': ['image/jpeg', 'image/png', 'image/gif', 'image/webp']
            },
            'document': {
                'folder': 'document_messages',
                'allowed_extensions': ['.pdf', '.doc', '.docx', '.txt', '.rtf'],
                'max_size_mb': 20,  # 20MB для документов
                'mime_types': ['application/pdf', 'application/msword', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document', 'text/plain', 'application/rtf']
            }
        }
    
    def _get_file_type(self, filename: str, mime_type: str) -> str:
        """Определяет тип файла на основе расширения и MIME типа"""
        extension = Path(filename).suffix.lower()
        
        # Проверяем по расширению
        for file_type, config in self.file_type_config.items():
            if extension in config['allowed_extensions']:
                return file_type
        
        # Проверяем по MIME типу
        for file_type, config in self.file_type_config.items():
            if mime_type in config['mime_types']:
                return file_type
        
        # Дополнительные проверки по MIME типу
        if mime_type.startswith('audio/'):
            return 'voice'
        elif mime_type.startswith('video/'):
            return 'video'
        elif mime_type.startswith('image/'):
            return 'photo'
        elif mime_type.startswith('application/') or mime_type.startswith('text/'):
            return 'document'
        
        return 'document'  # По умолчанию
    
    def _validate_file(self, file: UploadFile, file_type: str) -> None:
        """Валидирует файл перед загрузкой"""
        if file_type not in self.file_type_config:
            raise MediaFileTypeNotSupportedError(f"Неподдерживаемый тип файла: {file_type}")
        
        config = self.file_type_config[file_type]
        extension = Path(file.filename).suffix.lower()
        
        # Проверяем расширение
        if extension not in config['allowed_extensions']:
            raise MediaFileValidationError(f"Неподдерживаемое расширение файла: {extension}")
        
        # Проверяем MIME тип
        if file.content_type and file.content_type not in config['mime_types']:
            raise MediaFileValidationError(f"Неподдерживаемый MIME тип: {file.content_type}")
        
        # Проверяем размер файла
        if hasattr(file, 'size') and file.size:
            max_size_bytes = config['max_size_mb'] * 1024 * 1024
            if file.size > max_size_bytes:
                raise MediaFileSizeExceededError(f"Файл слишком большой. Максимальный размер: {config['max_size_mb']}MB")
    
    async def upload_file(self, file: UploadFile, user_id: int) -> Dict[str, Any]:
        """Универсальный метод для загрузки приватного файла любого типа"""
        try:
            mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or 'application/octet-stream'
            file_type = self._get_file_type(file.filename, mime_type)
            
            self._validate_file(file, file_type)
            config = self.file_type_config[file_type]
            
            file_content = await file.read()
            file_size = len(file_content)
            
            # Дополнительная проверка размера
            max_size_bytes = config['max_size_mb'] * 1024 * 1024
            if file_size > max_size_bytes:
                raise MediaFileSizeExceededError(f"Файл слишком большой. Максимальный размер: {config['max_size_mb']}MB")
            
            # Загружаем в приватный S3
            file_key = await self.private_s3_service.upload_file(
                file=file_content,
                filename=file.filename,
                folder=config['folder']
            )
            
            # Создаем запись в БД
            file_data = {
                'filename': file.filename,
                'file_key': file_key,
                'file_type': file_type,
                'mime_type': mime_type,
                'file_size': file_size,
                'folder': config['folder']
            }
            
            private_file = await self.private_media_file_manager.create_private_file(file_data)
            
            # Генерируем временную ссылку
            download_url = await self.private_s3_service.generate_presigned_url(file_key)
            
            app_logger.info(f"Приватный файл загружен: {file_key} пользователем {user_id}, тип: {file_type}")
            
            return {
                'id': private_file.id,
                'filename': private_file.filename,
                'file_key': private_file.file_key,
                'file_type': private_file.file_type,
                'mime_type': private_file.mime_type,
                'file_size': private_file.file_size,
                'folder': private_file.folder,
                'download_url': download_url,
                'created_at': private_file.created_at
            }
            
        except (MediaFileValidationError, MediaFileTypeNotSupportedError, MediaFileSizeExceededError):
            raise
        except Exception as e:
            app_logger.error(f"Ошибка загрузки приватного файла: {e}")
            raise MediaFileUploadError("Ошибка загрузки приватного файла")

    async def upload_voice_message(self, file: UploadFile, user_id: int) -> Dict[str, Any]:
        """Загружает голосовое сообщение"""
        try:
            mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or 'audio/mpeg'
            file_type = 'voice'
            
            self._validate_file(file, file_type)
            config = self.file_type_config[file_type]
            
            file_content = await file.read()
            file_size = len(file_content)
            
            # Дополнительная проверка размера
            max_size_bytes = config['max_size_mb'] * 1024 * 1024
            if file_size > max_size_bytes:
                raise MediaFileSizeExceededError(f"Файл слишком большой. Максимальный размер: {config['max_size_mb']}MB")
            
            # Загружаем в приватный S3
            file_key = await self.private_s3_service.upload_file(
                file=file_content,
                filename=file.filename,
                folder=config['folder']
            )
            
            # Создаем запись в БД
            file_data = {
                'filename': file.filename,
                'file_key': file_key,
                'file_type': file_type,
                'mime_type': mime_type,
                'file_size': file_size,
                'folder': config['folder']
            }
            
            private_file = await self.private_media_file_manager.create_private_file(file_data)
            
            # Генерируем временную ссылку
            download_url = await self.private_s3_service.generate_presigned_url(file_key)
            
            app_logger.info(f"Голосовое сообщение загружено: {file_key} пользователем {user_id}")
            
            return {
                'id': private_file.id,
                'filename': private_file.filename,
                'file_key': private_file.file_key,
                'file_type': private_file.file_type,
                'mime_type': private_file.mime_type,
                'file_size': private_file.file_size,
                'folder': private_file.folder,
                'download_url': download_url,
                'created_at': private_file.created_at
            }
            
        except (MediaFileValidationError, MediaFileTypeNotSupportedError, MediaFileSizeExceededError):
            raise
        except Exception as e:
            app_logger.error(f"Ошибка загрузки голосового сообщения: {e}")
            raise MediaFileUploadError("Ошибка загрузки голосового сообщения")
    
    async def upload_video_message(self, file: UploadFile, user_id: int) -> Dict[str, Any]:
        """Загружает видео сообщение"""
        try:
            mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or 'video/mp4'
            file_type = 'video'
            
            self._validate_file(file, file_type)
            config = self.file_type_config[file_type]
            
            file_content = await file.read()
            file_size = len(file_content)
            
            # Дополнительная проверка размера
            max_size_bytes = config['max_size_mb'] * 1024 * 1024
            if file_size > max_size_bytes:
                raise MediaFileSizeExceededError(f"Файл слишком большой. Максимальный размер: {config['max_size_mb']}MB")
            
            # Загружаем в приватный S3
            file_key = await self.private_s3_service.upload_file(
                file=file_content,
                filename=file.filename,
                folder=config['folder']
            )
            
            # Создаем запись в БД
            file_data = {
                'filename': file.filename,
                'file_key': file_key,
                'file_type': file_type,
                'mime_type': mime_type,
                'file_size': file_size,
                'folder': config['folder']
            }
            
            private_file = await self.private_media_file_manager.create_private_file(file_data)
            
            # Генерируем временную ссылку
            download_url = await self.private_s3_service.generate_presigned_url(file_key)
            
            app_logger.info(f"Видео сообщение загружено: {file_key} пользователем {user_id}")
            
            return {
                'id': private_file.id,
                'filename': private_file.filename,
                'file_key': private_file.file_key,
                'file_type': private_file.file_type,
                'mime_type': private_file.mime_type,
                'file_size': private_file.file_size,
                'folder': private_file.folder,
                'download_url': download_url,
                'created_at': private_file.created_at
            }
            
        except (MediaFileValidationError, MediaFileTypeNotSupportedError, MediaFileSizeExceededError):
            raise
        except Exception as e:
            app_logger.error(f"Ошибка загрузки видео сообщения: {e}")
            raise MediaFileUploadError("Ошибка загрузки видео сообщения")
    
    async def upload_photo_message(self, file: UploadFile, user_id: int) -> Dict[str, Any]:
        """Загружает фото сообщение"""
        try:
            mime_type = file.content_type or mimetypes.guess_type(file.filename)[0] or 'image/jpeg'
            file_type = 'photo'
            
            self._validate_file(file, file_type)
            config = self.file_type_config[file_type]
            
            file_content = await file.read()
            file_size = len(file_content)
            
            # Дополнительная проверка размера
            max_size_bytes = config['max_size_mb'] * 1024 * 1024
            if file_size > max_size_bytes:
                raise MediaFileSizeExceededError(f"Файл слишком большой. Максимальный размер: {config['max_size_mb']}MB")
            
            # Загружаем в приватный S3
            file_key = await self.private_s3_service.upload_file(
                file=file_content,
                filename=file.filename,
                folder=config['folder']
            )
            
            # Создаем запись в БД
            file_data = {
                'filename': file.filename,
                'file_key': file_key,
                'file_type': file_type,
                'mime_type': mime_type,
                'file_size': file_size,
                'folder': config['folder']
            }
            
            private_file = await self.private_media_file_manager.create_private_file(file_data)
            
            # Генерируем временную ссылку
            download_url = await self.private_s3_service.generate_presigned_url(file_key)
            
            app_logger.info(f"Фото сообщение загружено: {file_key} пользователем {user_id}")
            
            return {
                'id': private_file.id,
                'filename': private_file.filename,
                'file_key': private_file.file_key,
                'file_type': private_file.file_type,
                'mime_type': private_file.mime_type,
                'file_size': private_file.file_size,
                'folder': private_file.folder,
                'download_url': download_url,
                'created_at': private_file.created_at
            }
            
        except (MediaFileValidationError, MediaFileTypeNotSupportedError, MediaFileSizeExceededError):
            raise
        except Exception as e:
            app_logger.error(f"Ошибка загрузки фото сообщения: {e}")
            raise MediaFileUploadError("Ошибка загрузки фото сообщения")
    
    async def get_file(self, file_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о приватном файле"""
        try:
            private_file = await self.private_media_file_manager.get_obj_by_id(file_id)
            
            if not private_file:
                return None
            
            download_url = await self.private_s3_service.generate_presigned_url(private_file.file_key)
            
            return {
                'id': private_file.id,
                'filename': private_file.filename,
                'file_key': private_file.file_key,
                'file_type': private_file.file_type,
                'mime_type': private_file.mime_type,
                'file_size': private_file.file_size,
                'folder': private_file.folder,
                'message_id': private_file.message_id,
                'download_url': download_url,
                'created_at': private_file.created_at,
                'updated_at': private_file.updated_at
            }
            
        except Exception as e:
            app_logger.error(f"Ошибка получения файла {file_id}: {e}")
            return None
    
    async def get_user_files(self, file_type: Optional[str] = None,
                           limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """Получить приватные файлы"""
        try:
            if file_type == 'voice':
                private_files = await self.private_media_file_manager.get_voice_messages(limit, offset)
            elif file_type == 'video':
                private_files = await self.private_media_file_manager.get_video_messages(limit, offset)
            else:
                # Получаем все файлы
                private_files = []
            
            result = []
            for private_file in private_files:
                download_url = await self.private_s3_service.generate_presigned_url(private_file.file_key)
                result.append({
                    'id': private_file.id,
                    'filename': private_file.filename,
                    'file_key': private_file.file_key,
                    'file_type': private_file.file_type,
                    'mime_type': private_file.mime_type,
                    'file_size': private_file.file_size,
                    'folder': private_file.folder,
                    'message_id': private_file.message_id,
                    'download_url': download_url,
                    'created_at': private_file.created_at,
                    'updated_at': private_file.updated_at
                })
            
            return result
            
        except Exception as e:
            app_logger.error(f"Ошибка получения файлов: {e}")
            return []
    
    
    async def attach_to_message(self, file_id: int, message_id: int) -> bool:
        """Прикрепить файл к сообщению"""
        try:
            return await self.private_media_file_manager.attach_to_message(file_id, message_id)
            
        except Exception as e:
            app_logger.error(f"Ошибка прикрепления файла {file_id} к сообщению {message_id}: {e}")
            return False
    
    async def detach_from_message(self, file_id: int) -> bool:
        """Открепить файл от сообщения"""
        try:
            return await self.private_media_file_manager.detach_from_message(file_id)
            
        except Exception as e:
            app_logger.error(f"Ошибка открепления файла {file_id}: {e}")
            return False
    
    async def delete_file(self, file_id: int) -> bool:
        """Удалить приватный файл"""
        try:
            private_file = await self.private_media_file_manager.get_obj_by_id(file_id)
            
            if not private_file:
                return False
            
            # Удаляем из приватного S3
            await self.private_s3_service.delete_file(private_file.file_key)
            
            # Удаляем из БД
            await self.private_media_file_manager.delete_obj(private_file.id)
            
            app_logger.info(f"Приватный файл удален: {private_file.file_key}")
            return True
            
        except Exception as e:
            app_logger.error(f"Ошибка удаления файла {file_id}: {e}")
            return False
