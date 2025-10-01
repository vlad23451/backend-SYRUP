from core.config import settings
from exceptions.s3 import S3ValidationError
from fastapi import UploadFile

class FileValidationService:
    @staticmethod
    async def validate_avatar_file(file: UploadFile) -> None:
        if file.size and file.size > settings.max_file_size:
            raise S3ValidationError(
                f"Файл слишком большой. Максимальный размер: {settings.max_file_size // 1024 // 1024} МБ"
            )
        
        if file.content_type not in settings.allowed_file_types:
            allowed_types_str = ", ".join(settings.allowed_file_types)
            raise S3ValidationError(
                f"Неподдерживаемый тип файла. Разрешенные типы: {allowed_types_str}"
            )
        
        image_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]

        if file.content_type not in image_types:
            raise S3ValidationError(
                "Аватар должен быть изображением (JPEG, PNG, GIF или WebP)"
            )
    
    @staticmethod
    async def validate_file_general(file: UploadFile) -> None:
        if file.size and file.size > settings.max_file_size:
            raise S3ValidationError(
                f"Файл слишком большой. Максимальный размер: {settings.max_file_size // 1024 // 1024} МБ"
            )
        
        if file.content_type not in settings.allowed_file_types:
            allowed_types_str = ", ".join(settings.allowed_file_types)
            raise S3ValidationError(
                f"Неподдерживаемый тип файла. Разрешенные типы: {allowed_types_str}"
            )
    
    @staticmethod
    def get_image_types() -> list[str]:
        return ["image/jpeg", "image/png", "image/gif", "image/webp"]
    
    @staticmethod
    def get_video_types() -> list[str]:
        return ["video/mp4", "video/webm", "video/ogg"]
    
    @staticmethod
    def get_audio_types() -> list[str]:
        return ["audio/mpeg", "audio/wav", "audio/ogg"]
