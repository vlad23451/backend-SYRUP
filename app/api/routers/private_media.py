from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import UploadFile
from fastapi import File
from fastapi import Query

from api.dependencies.pagination import get_large_pagination
from api.dependencies.auth import get_current_user

from core.logger import app_logger

from database.managers.private_media_file_manager import PrivateMediaFileManager
from database.models.user import User

from exceptions.media_files import MediaFileNotFoundError
from exceptions.media_files import MediaFileAccessDeniedError

from schemas.private_media import (
    PrivateMediaFileResponse,
    PrivateMediaFileUploadResponse,
    PrivateMediaFileListResponse,
    PrivateMediaFileAttachRequest,
    PrivateMediaFileDetachRequest
)

from services.private_media_service import PrivateMediaService
from services.error_handler_service import handle_api_errors

private_media_router = APIRouter(prefix="/private-media", tags=["Приватные медиафайлы"])

private_media_file_manager = PrivateMediaFileManager()
private_media_service = PrivateMediaService(private_media_file_manager)

@private_media_router.post("/upload",
                          summary="Загрузить приватный файл",
                          description="Загружает файл любого поддерживаемого типа (голосовые, видео, фото, документы) в приватное хранилище")
@handle_api_errors("Ошибка загрузки приватного файла")
async def upload_private_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
) -> PrivateMediaFileUploadResponse:
    """Загружает приватный файл любого поддерживаемого типа"""
    result = await private_media_service.upload_file(
        file=file,
        user_id=current_user.id
    )
    
    app_logger.info(f"Пользователь {current_user.id} загрузил приватный файл: {result['filename']}, тип: {result['file_type']}")
    return PrivateMediaFileUploadResponse(**result)

@private_media_router.get("/files",
                         summary="Получить приватные файлы пользователя",
                         description="Получает список приватных файлов пользователя с фильтрацией")
@handle_api_errors("Ошибка получения приватных файлов")
async def get_user_private_files(
    file_type: str = Query(None, description="Тип файла для фильтрации"),
    pagination: tuple[int, int] = Depends(get_large_pagination),
    current_user: User = Depends(get_current_user)
) -> PrivateMediaFileListResponse:
    """Получает приватные файлы пользователя"""
    limit, offset = pagination
    files = await private_media_service.get_user_files(
        file_type=file_type,
        limit=limit,
        offset=offset
    )
    
    total = len(files)  # Временное решение, пока не реализован подсчет
    
    return PrivateMediaFileListResponse(
        files=[PrivateMediaFileResponse(**file) for file in files],
        total=total,
        page=offset // limit + 1,
        per_page=limit
    )

@private_media_router.get("/files/{file_id}",
                         summary="Получить информацию о приватном файле",
                         description="Получает информацию о конкретном приватном файле")
@handle_api_errors("Ошибка получения файла")
async def get_private_file(
    file_id: int,
    current_user: User = Depends(get_current_user)
) -> PrivateMediaFileResponse:
    """Получает информацию о приватном файле"""
    file_info = await private_media_service.get_file(file_id)
    
    if not file_info:
        raise MediaFileNotFoundError("Файл не найден или у вас нет прав доступа")
    
    return PrivateMediaFileResponse(**file_info)


@private_media_router.post("/attach",
                          summary="Прикрепить файл к сообщению",
                          description="Прикрепляет приватный файл к сообщению в чате")
@handle_api_errors("Ошибка прикрепления файла")
async def attach_file_to_message(
    attach_request: PrivateMediaFileAttachRequest,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Прикрепляет файл к сообщению"""
    success = await private_media_service.attach_to_message(
        file_id=attach_request.file_id,
        message_id=attach_request.message_id
    )
    
    if not success:
        raise MediaFileAccessDeniedError("Файл не найден или у вас нет прав на его прикрепление")
    
    app_logger.info(f"Пользователь {current_user.id} прикрепил файл {attach_request.file_id} к сообщению {attach_request.message_id}")
    return {"message": "Файл успешно прикреплен к сообщению"}

@private_media_router.post("/detach",
                          summary="Открепить файл от сообщения",
                          description="Открепляет приватный файл от сообщения")
@handle_api_errors("Ошибка открепления файла")
async def detach_file_from_message(
    detach_request: PrivateMediaFileDetachRequest,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Открепляет файл от сообщения"""
    success = await private_media_service.detach_from_message(
        file_id=detach_request.file_id
    )
    
    if not success:
        raise MediaFileAccessDeniedError("Файл не найден или у вас нет прав на его открепление")
    
    app_logger.info(f"Пользователь {current_user.id} открепил файл {detach_request.file_id} от сообщения")
    return {"message": "Файл успешно откреплен от сообщения"}

@private_media_router.delete("/files/{file_id}",
                            summary="Удалить приватный файл",
                            description="Удаляет приватный файл из хранилища и базы данных")
@handle_api_errors("Ошибка удаления файла")
async def delete_private_file(
    file_id: int,
    current_user: User = Depends(get_current_user)
) -> dict:
    """Удаляет приватный файл"""
    success = await private_media_service.delete_file(file_id)
    
    if not success:
        raise MediaFileAccessDeniedError("Файл не найден или у вас нет прав на его удаление")
    
    app_logger.info(f"Пользователь {current_user.id} удалил приватный файл {file_id}")
    return {"message": "Файл успешно удален"}

@private_media_router.get("/voice-messages",
                         summary="Получить голосовые сообщения",
                         description="Получает голосовые сообщения пользователя")
@handle_api_errors("Ошибка получения голосовых сообщений")
async def get_voice_messages(
    chat_id: int = Query(None, description="ID чата для фильтрации"),
    pagination: tuple[int, int] = Depends(get_large_pagination),
    current_user: User = Depends(get_current_user)
) -> List[PrivateMediaFileResponse]:
    """Получает голосовые сообщения"""
    limit, offset = pagination
    files = await private_media_file_manager.get_voice_messages(
        limit=limit,
        offset=offset
    )
    
    result = []
    for file in files:
        download_url = await private_media_service.private_s3_service.generate_presigned_url(file.file_key)
        result.append(PrivateMediaFileResponse(
            id=file.id,
            filename=file.filename,
            file_key=file.file_key,
            file_type=file.file_type,
            mime_type=file.mime_type,
            file_size=file.file_size,
            folder=file.folder,
            message_id=file.message_id,
            download_url=download_url,
            created_at=file.created_at,
            updated_at=file.updated_at
        ))
    
    return result

@private_media_router.get("/video-messages",
                         summary="Получить видео сообщения",
                         description="Получает видео сообщения пользователя")
@handle_api_errors("Ошибка получения видео сообщений")
async def get_video_messages(
    chat_id: int = Query(None, description="ID чата для фильтрации"),
    pagination: tuple[int, int] = Depends(get_large_pagination),
    current_user: User = Depends(get_current_user)
) -> List[PrivateMediaFileResponse]:
    """Получает видео сообщения"""
    limit, offset = pagination
    files = await private_media_file_manager.get_video_messages(
        limit=limit,
        offset=offset
    )
    
    result = []
    for file in files:
        download_url = await private_media_service.private_s3_service.generate_presigned_url(file.file_key)
        result.append(PrivateMediaFileResponse(
            id=file.id,
            filename=file.filename,
            file_key=file.file_key,
            file_type=file.file_type,
            mime_type=file.mime_type,
            file_size=file.file_size,
            folder=file.folder,
            message_id=file.message_id,
            download_url=download_url,
            created_at=file.created_at,
            updated_at=file.updated_at
        ))
    
    return result
