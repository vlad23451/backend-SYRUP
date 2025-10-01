from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import UploadFile
from fastapi import File
from fastapi import Form
from fastapi import Query

from api.dependencies.pagination import get_large_pagination
from api.dependencies.auth import get_current_user

from api.docs.media import media_upload_responses
from api.docs.media import media_file_responses
from api.docs.media import media_file_list_responses
from api.docs.media import media_attach_responses
from api.docs.media import upload_file_description
from api.docs.media import get_user_files_description
from api.docs.media import get_file_description
from api.docs.media import update_file_description
from api.docs.media import delete_file_description
from api.docs.media import get_history_files_description
from api.docs.media import attach_file_description
from api.docs.media import detach_file_description
from api.docs.media import get_public_files_description

from core.logger import app_logger

from database.managers.media_file_manager import MediaFileManager
from database.models.user import User

from exceptions.media_files import MediaFileNotFoundError
from exceptions.media_files import MediaFileAccessDeniedError

from schemas.media import MediaFileResponse
from schemas.media import MediaFileUploadResponse
from schemas.media import MediaFileListResponse
from schemas.media import MediaFileUpdate
from schemas.media import MediaFileAttachRequest
from schemas.media import MediaFileDetachRequest

from services.media_service import MediaService
from services.error_handler_service import handle_api_errors

media_router = APIRouter(prefix="/media", tags=["media"])

media_file_manager = MediaFileManager()
media_service = MediaService(media_file_manager)

@media_router.post("/upload",
                   summary="Загрузить файл",
                   responses=media_upload_responses,
                   description=upload_file_description)
@handle_api_errors("Ошибка загрузки файла")
async def upload_file(file: UploadFile = File(...),
                      description: str | None = Form(None),
                      is_public: bool = Form(False),
                      current_user: User = Depends(get_current_user)) -> MediaFileUploadResponse:
    result = await media_service.upload_file(
        file=file,
        user_id=current_user.id,
        description=description,
        is_public=is_public
    )
    
    app_logger.info(f"Пользователь {current_user.id} загрузил файл: {result['filename']}")
    return MediaFileUploadResponse(**result)

@media_router.get("/files",
                  summary="Получить файлы пользователя",
                  responses=media_file_list_responses,
                  description=get_user_files_description)
@handle_api_errors("Ошибка получения файлов пользователя")
async def get_user_files(file_type: str | None = Query(None),
                         pagination: tuple[int, int] = Depends(get_large_pagination),
                         current_user: User = Depends(get_current_user)
) -> MediaFileListResponse:
    """Получает файлы пользователя с фильтрацией по типу и пагинацией."""
    limit, offset = pagination
    files = await media_service.get_user_files(
        user_id=current_user.id,
        file_type=file_type,
        limit=limit,
        offset=offset
    )
    
    total = await media_service.media_file_manager.count_by_user_id(current_user.id)
    
    return MediaFileListResponse(
        files=[MediaFileResponse(**file) for file in files],
        total=total,
        page=offset // limit + 1,
        per_page=limit
    )

@media_router.get("/files/{file_id}",
                  summary="Получить информацию о файле",
                  responses=media_file_responses,
                  description=get_file_description)
@handle_api_errors("Ошибка получения файла")
async def get_file(file_id: int,
                   current_user: User = Depends(get_current_user)) -> MediaFileResponse:
    """Получает информацию о файле, если у пользователя есть права доступа."""
    file_info = await media_service.get_file(file_id, current_user.id)
    
    if not file_info:
        raise MediaFileNotFoundError("Файл не найден или у вас нет прав доступа")
    
    return MediaFileResponse(**file_info)

@media_router.put("/files/{file_id}",
                  summary="Обновить информацию о файле",
                  responses=media_file_responses,
                  description=update_file_description)
@handle_api_errors("Ошибка обновления файла")
async def update_file(file_id: int,
                      file_update: MediaFileUpdate,
                      current_user: User = Depends(get_current_user)) -> MediaFileResponse:
    """Обновляет описание и публичность файла."""
    success = await media_service.update_file(
        file_id=file_id,
        user_id=current_user.id,
        description=file_update.description,
        is_public=file_update.is_public
    )
    
    if not success:
        raise MediaFileAccessDeniedError("Файл не найден или у вас нет прав на его изменение")
    
    file_info = await media_service.get_file(file_id, current_user.id)
    return MediaFileResponse(**file_info)

@media_router.delete("/files/{file_id}",
                     summary="Удалить файл",
                     responses=media_attach_responses,
                     description=delete_file_description)
@handle_api_errors("Ошибка удаления файла")
async def delete_file(file_id: int,
                      current_user: User = Depends(get_current_user)) -> dict:
    """Удаляет файл из S3 и базы данных."""
    success = await media_service.delete_file(file_id, current_user.id)
    
    if not success:
        raise MediaFileAccessDeniedError("Файл не найден или у вас нет прав на его удаление")
    
    app_logger.info(f"Пользователь {current_user.id} удалил файл {file_id}")
    return {"message": "Файл успешно удален"}

@media_router.get("/history/{history_id}/files",
                  summary="Получить файлы истории",
                  responses=media_file_list_responses,
                  description=get_history_files_description)
@handle_api_errors("Ошибка получения файлов истории")
async def get_history_files(history_id: int) -> List[MediaFileResponse]:
    """Получает все файлы, прикрепленные к истории."""
    files = await media_service.get_history_files(history_id)
    return [MediaFileResponse(**file) for file in files]

@media_router.get("/comment/{comment_id}/files",
                  summary="Получить файлы комментария",
                  responses=media_file_list_responses,
                  description="Получить все файлы, прикрепленные к комментарию")
@handle_api_errors("Ошибка получения файлов комментария")
async def get_comment_files(comment_id: int) -> List[MediaFileResponse]:
    """Получает все файлы, прикрепленные к комментарию."""
    files = await media_service.get_comment_files(comment_id)
    return [MediaFileResponse(**file) for file in files]

@media_router.post("/attach",
                   summary="Прикрепить файл к истории или комментарию",
                   responses=media_attach_responses,
                   description=attach_file_description)
@handle_api_errors("Ошибка прикрепления файла")
async def attach_file(attach_request: MediaFileAttachRequest,
                     current_user: User = Depends(get_current_user)) -> dict:
    """Прикрепляет файл к истории или комментарию."""
    success = await media_service.attach_file(
        file_id=attach_request.file_id,
        history_id=attach_request.history_id,
        comment_id=attach_request.comment_id,
        user_id=current_user.id
    )
    
    if not success:
        raise MediaFileAccessDeniedError("Файл не найден или у вас нет прав на его прикрепление")
    
    target = f"истории {attach_request.history_id}" if attach_request.history_id else f"комментарию {attach_request.comment_id}"
    app_logger.info(f"Пользователь {current_user.id} прикрепил файл {attach_request.file_id} к {target}")
    return {"message": f"Файл успешно прикреплен к {target}"}

@media_router.post("/detach", 
                   summary="Открепить файл от истории или комментария",
                   responses=media_attach_responses,
                   description=detach_file_description)
@handle_api_errors("Ошибка открепления файла")
async def detach_file(detach_request: MediaFileDetachRequest,
                     current_user: User = Depends(get_current_user)) -> dict:
    """Открепляет файл от истории или комментария."""
    success = await media_service.detach_file(
        file_id=detach_request.file_id,
        history_id=detach_request.history_id,
        comment_id=detach_request.comment_id,
        user_id=current_user.id
    )
    
    if not success:
        raise MediaFileAccessDeniedError("Файл не найден или у вас нет прав на его открепление")
    
    target = f"истории {detach_request.history_id}" if detach_request.history_id else f"комментарию {detach_request.comment_id}"
    app_logger.info(f"Пользователь {current_user.id} открепил файл {detach_request.file_id} от {target}")
    return {"message": f"Файл успешно откреплен от {target}"}

@media_router.get("/public", 
                  summary="Получить публичные файлы",
                  responses=media_file_list_responses,
                  description=get_public_files_description)
@handle_api_errors("Ошибка получения публичных файлов")
async def get_public_files(pagination: tuple[int, int] = Depends(get_large_pagination)) -> MediaFileListResponse:
    """Получает все публичные файлы с пагинацией."""
    limit, offset = pagination
    result = await media_service.get_public_files(limit, offset)
    
    return MediaFileListResponse(
        files=[MediaFileResponse(**file) for file in result['files']],
        total=result['total'],
        page=result['page'],
        per_page=result['per_page']
    )
