"""Сервис для валидации загружаемых файлов."""

from core.config import settings
from exceptions.s3 import S3ValidationError
from fastapi import UploadFile


class FileValidationService:
    """Сервис для валидации различных типов файлов."""
    
    @staticmethod
    async def validate_avatar_file(file: UploadFile) -> None:
        """Валидирует загружаемый файл аватара.
        
        Проверяет:
        - Размер файла (не больше max_file_size)
        - Общий тип файла (должен быть в allowed_file_types)
        - Специфический тип для аватара (только изображения)
        
        Args:
            file: Загружаемый файл
            
        Raises:
            S3ValidationError: Файл не прошел валидацию
            
        Example:
            >>> await FileValidationService.validate_avatar_file(upload_file)
            # Raises S3ValidationError if validation fails
        """
        # Проверяем размер файла
        if file.size and file.size > settings.max_file_size:
            raise S3ValidationError(
                f"Файл слишком большой. Максимальный размер: {settings.max_file_size // 1024 // 1024} МБ"
            )
        
        # Проверяем тип файла
        if file.content_type not in settings.allowed_file_types:
            allowed_types_str = ", ".join(settings.allowed_file_types)
            raise S3ValidationError(
                f"Неподдерживаемый тип файла. Разрешенные типы: {allowed_types_str}"
            )
        
        # Проверяем, что это изображение (для аватаров)
        image_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
        if file.content_type not in image_types:
            raise S3ValidationError(
                "Аватар должен быть изображением (JPEG, PNG, GIF или WebP)"
            )
    
    @staticmethod
    async def validate_file_general(file: UploadFile) -> None:
        """Общая валидация файла (размер и тип).
        
        Проверяет только базовые параметры без специфических требований.
        
        Args:
            file: Загружаемый файл
            
        Raises:
            S3ValidationError: Файл не прошел валидацию
            
        Example:
            >>> await FileValidationService.validate_file_general(upload_file)
            # Raises S3ValidationError if validation fails
        """
        # Проверяем размер файла
        if file.size and file.size > settings.max_file_size:
            raise S3ValidationError(
                f"Файл слишком большой. Максимальный размер: {settings.max_file_size // 1024 // 1024} МБ"
            )
        
        # Проверяем тип файла
        if file.content_type not in settings.allowed_file_types:
            allowed_types_str = ", ".join(settings.allowed_file_types)
            raise S3ValidationError(
                f"Неподдерживаемый тип файла. Разрешенные типы: {allowed_types_str}"
            )
    
    @staticmethod
    def get_image_types() -> list[str]:
        """Получить список разрешенных типов изображений.
        
        Returns:
            list[str]: Список MIME-типов изображений
            
        Example:
            >>> types = FileValidationService.get_image_types()
            >>> print(types)  # ["image/jpeg", "image/png", "image/gif", "image/webp"]
        """
        return ["image/jpeg", "image/png", "image/gif", "image/webp"]
    
    @staticmethod
    def get_video_types() -> list[str]:
        """Получить список разрешенных типов видео.
        
        Returns:
            list[str]: Список MIME-типов видео
            
        Example:
            >>> types = FileValidationService.get_video_types()
            >>> print(types)  # ["video/mp4", "video/webm", "video/ogg"]
        """
        return ["video/mp4", "video/webm", "video/ogg"]
    
    @staticmethod
    def get_audio_types() -> list[str]:
        """Получить список разрешенных типов аудио.
        
        Returns:
            list[str]: Список MIME-типов аудио
            
        Example:
            >>> types = FileValidationService.get_audio_types()
            >>> print(types)  # ["audio/mpeg", "audio/wav", "audio/ogg"]
        """
        return ["audio/mpeg", "audio/wav", "audio/ogg"]
