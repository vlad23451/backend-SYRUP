from datetime import datetime
from typing import List

from pydantic import BaseModel
from pydantic import Field
from pydantic import ConfigDict

class MediaFileBase(BaseModel):
    filename: str = Field(..., description="Оригинальное имя файла")
    file_type: str = Field(..., description="Тип файла (image, video, audio, document)")
    mime_type: str = Field(..., description="MIME тип файла")
    file_size: int = Field(..., description="Размер файла в байтах")
    folder: str = Field(..., description="Папка в S3")
    description: str | None = Field(None, description="Описание файла")
    is_public: bool = Field(False, description="Публичный ли файл")

class MediaFileCreate(MediaFileBase):
    history_id: int | None = Field(None, description="ID истории, к которой прикрепляется файл")

class MediaFileUpdate(BaseModel):
    description: str | None = Field(None, description="Описание файла")
    is_public: bool | None = Field(None, description="Публичный ли файл")

class MediaFileResponse(MediaFileBase):
    id: int = Field(..., description="ID файла")
    file_key: str = Field(..., description="Ключ файла в S3")
    user_id: int = Field(..., description="ID пользователя")
    history_id: int | None = Field(None, description="ID истории")
    created_at: datetime = Field(..., description="Дата создания")
    updated_at: datetime = Field(..., description="Дата обновления")
    
    model_config = ConfigDict(from_attributes=True)

class MediaFileUploadResponse(BaseModel):
    id: int = Field(..., description="ID файла")
    filename: str = Field(..., description="Оригинальное имя файла")
    file_key: str = Field(..., description="Ключ файла в S3")
    file_type: str = Field(..., description="Тип файла")
    mime_type: str = Field(..., description="MIME тип файла")
    file_size: int = Field(..., description="Размер файла в байтах")
    folder: str = Field(..., description="Папка в S3")
    download_url: str | None = Field(None, description="Временная ссылка для скачивания")
    created_at: datetime = Field(..., description="Дата создания")

class MediaFileListResponse(BaseModel):
    files: List[MediaFileResponse] = Field(..., description="Список файлов")
    total: int = Field(..., description="Общее количество файлов")
    page: int = Field(..., description="Номер страницы")
    per_page: int = Field(..., description="Количество файлов на странице")

class MediaFileAttachRequest(BaseModel):
    file_id: int = Field(..., description="ID файла для прикрепления")
    history_id: int = Field(..., description="ID истории")

class MediaFileDetachRequest(BaseModel):
    file_id: int = Field(..., description="ID файла для открепления")
    history_id: int = Field(..., description="ID истории")
