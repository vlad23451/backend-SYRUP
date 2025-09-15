import os
from pathlib import Path
from typing import Optional, Tuple
from fastapi import UploadFile, HTTPException, status
from PIL import Image
import mimetypes

from database.managers.file_manager import FileManager
from database.models.file import FileType
from schemas.file import FileOut, FileCreate
from core.logger import app_logger

class FileService:
    def __init__(self):
        self.file_manager = FileManager()

    async def upload_file(self, file: UploadFile, user_id: int, history_id: Optional[int] = None) -> FileOut:
        """Загружает файл и создает запись в базе данных."""
        
        # Проверяем тип файла
        if not self.file_manager.is_valid_file_type(file.content_type):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Неподдерживаемый тип файла: {file.content_type}"
            )

        # Определяем тип файла
        file_type = self.file_manager._get_file_type_from_mime(file.content_type)
        
        # Проверяем размер файла
        max_size = self.file_manager.get_max_file_size(file_type)
        file_size = 0
        
        # Читаем файл и сохраняем его
        filename = self.file_manager._generate_filename(file.filename, file_type)
        file_path = self.file_manager._get_file_path(filename, file_type)
        
        try:
            with open(file_path, "wb") as buffer:
                while chunk := await file.read(8192):  # 8KB chunks
                    file_size += len(chunk)
                    if file_size > max_size:
                        # Удаляем частично загруженный файл
                        os.remove(file_path)
                        raise HTTPException(
                            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                            detail=f"Файл слишком большой. Максимальный размер для {file_type.value}: {self.file_manager.get_file_size_mb(max_size)} MB"
                        )
                    buffer.write(chunk)
        except Exception as e:
            app_logger.error(f"Ошибка при загрузке файла: {e}")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Ошибка при загрузке файла"
            )

        # Обрабатываем метаданные для медиафайлов
        duration = None
        
        if file_type in [FileType.AUDIO, FileType.VIDEO]:
            duration = await self._extract_media_duration(file_path, file_type)

        # Создаем запись в базе данных
        file_data = {
            "filename": filename,
            "original_filename": file.filename,
            "file_path": file_path,
            "file_size": file_size,
            "mime_type": file.content_type,
            "file_type": file_type.value,
            "duration": duration,
            "history_id": history_id
        }

        file_record = await self.file_manager.create_file_record(file_data, user_id)
        
        app_logger.info(f"Файл загружен: {file.filename} ({self.file_manager.get_file_size_mb(file_size)} MB) пользователем {user_id}")
        
        return file_record


    async def _extract_media_duration(self, file_path: str, file_type: FileType) -> Optional[float]:
        """Извлекает длительность аудио или видео файла."""
        try:
            # Для извлечения длительности можно использовать ffmpeg или другие библиотеки
            # Пока возвращаем None
            return None
        except Exception as e:
            app_logger.warning(f"Не удалось извлечь длительность для {file_path}: {e}")
            return None

    async def create_thumbnail(self, file_path: str, file_type: FileType) -> Optional[str]:
        """Создает миниатюру для изображения или видео."""
        try:
            if file_type == FileType.IMAGE:
                return await self._create_image_thumbnail(file_path)
            elif file_type == FileType.VIDEO:
                return await self._create_video_thumbnail(file_path)
        except Exception as e:
            app_logger.warning(f"Не удалось создать миниатюру для {file_path}: {e}")
            return None

    async def _create_image_thumbnail(self, file_path: str) -> Optional[str]:
        """Создает миниатюру для изображения."""
        try:
            with Image.open(file_path) as img:
                # Создаем миниатюру 200x200
                img.thumbnail((200, 200), Image.Resampling.LANCZOS)
                
                # Сохраняем миниатюру
                thumbnail_path = file_path.replace('.', '_thumb.')
                img.save(thumbnail_path, quality=85, optimize=True)
                
                return thumbnail_path
        except Exception as e:
            app_logger.warning(f"Ошибка при создании миниатюры изображения: {e}")
            return None

    async def _create_video_thumbnail(self, file_path: str) -> Optional[str]:
        """Создает миниатюру для видео (требует ffmpeg)."""
        # Для создания миниатюр видео нужен ffmpeg
        # Пока возвращаем None
        return None

    async def get_file_stream(self, file_id: int) -> Tuple[Optional[str], Optional[str], Optional[str]]:
        """Возвращает поток файла для скачивания."""
        file_record = await self.file_manager.get_file_by_id(file_id)
        
        if not file_record:
            return None, None, None
        
        if not os.path.exists(file_record.file_path):
            app_logger.error(f"Файл не найден на диске: {file_record.file_path}")
            return None, None, None
        
        return file_record.file_path, file_record.original_filename, file_record.mime_type

    async def attach_file_to_history(self, file_id: int, history_id: int) -> bool:
        """Прикрепляет файл к истории."""
        return await self.file_manager.attach_file_to_history(file_id, history_id)

    async def detach_file_from_history(self, file_id: int) -> bool:
        """Открепляет файл от истории."""
        return await self.file_manager.detach_file_from_history(file_id)

    async def delete_file(self, file_id: int, user_id: int) -> bool:
        """Удаляет файл."""
        return await self.file_manager.delete_file(file_id, user_id)

    def get_file_info(self, file_path: str) -> dict:
        """Получает информацию о файле."""
        path = Path(file_path)
        if not path.exists():
            return {}
        
        stat = path.stat()
        mime_type, _ = mimetypes.guess_type(str(path))
        
        return {
            "size": stat.st_size,
            "mime_type": mime_type or "application/octet-stream",
            "modified": stat.st_mtime
        }
