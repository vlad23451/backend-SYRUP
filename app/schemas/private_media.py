from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel
from pydantic import Field
from pydantic import ConfigDict

class PrivateMediaFileBase(BaseModel):
    filename: str = Field(..., description="Оригинальное имя файла")
    file_type: str = Field(..., description="Тип файла (voice, video, photo, document)")
    mime_type: str = Field(..., description="MIME тип файла")
    file_size: int = Field(..., description="Размер файла в байтах")
    folder: str = Field(..., description="Папка в S3")

class PrivateMediaFileCreate(PrivateMediaFileBase):
    message_id: Optional[int] = Field(None, description="ID сообщения, к которому прикрепляется файл")

class PrivateMediaFileUpdate(BaseModel):
    pass

class PrivateMediaFileResponse(PrivateMediaFileBase):
    id: int = Field(..., description="ID файла")
    file_key: str = Field(..., description="Ключ файла в S3")
    message_id: Optional[int] = Field(None, description="ID сообщения")
    download_url: Optional[str] = Field(None, description="Временная ссылка для скачивания")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    
    model_config = ConfigDict(from_attributes=True)

class PrivateMediaFileUploadResponse(BaseModel):
    id: int = Field(..., description="ID файла")
    filename: str = Field(..., description="Оригинальное имя файла")
    file_key: str = Field(..., description="Ключ файла в S3")
    file_type: str = Field(..., description="Тип файла")
    mime_type: str = Field(..., description="MIME тип файла")
    file_size: int = Field(..., description="Размер файла в байтах")
    folder: str = Field(..., description="Папка в S3")
    download_url: Optional[str] = Field(None, description="Временная ссылка для скачивания")
    created_at: datetime = Field(..., description="Дата создания")

class PrivateMediaFileListResponse(BaseModel):
    files: List[PrivateMediaFileResponse] = Field(..., description="Список файлов")
    total: int = Field(..., description="Общее количество файлов")
    page: int = Field(..., description="Номер страницы")
    per_page: int = Field(..., description="Количество файлов на странице")

class VoiceMessageUploadRequest(BaseModel):
    """Запрос на загрузку голосового сообщения"""
    pass  # Пока нет дополнительных параметров

class VideoMessageUploadRequest(BaseModel):
    """Запрос на загрузку видео сообщения"""
    pass  # Пока нет дополнительных параметров

class PhotoMessageUploadRequest(BaseModel):
    """Запрос на загрузку фото сообщения"""
    pass  # Пока нет дополнительных параметров

class PrivateMediaFileAttachRequest(BaseModel):
    """Запрос на прикрепление приватного файла к сообщению"""
    file_id: int = Field(..., description="ID файла для прикрепления")
    message_id: int = Field(..., description="ID сообщения")

class PrivateMediaFileDetachRequest(BaseModel):
    """Запрос на открепление приватного файла от сообщения"""
    file_id: int = Field(..., description="ID файла для открепления")

class PrivateMediaFileSearchRequest(BaseModel):
    """Запрос на поиск приватных файлов"""
    file_type: Optional[str] = Field(None, description="Тип файла для фильтрации")
    limit: int = Field(50, ge=1, le=200, description="Максимальное количество результатов")
    offset: int = Field(0, ge=0, description="Смещение для пагинации")
