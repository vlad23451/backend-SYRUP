import datetime

from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status

from api.dependencies.auth import get_current_user
from api.dependencies.pagination import get_large_pagination

from api.docs.message import get_chats_description
from api.docs.message import get_chats_responses
from api.docs.message import search_messages_description
from api.docs.message import search_messages_responses

from core.logger import app_logger

from database.managers.message_manager import MessageManager
from database.managers.chat_manager import ChatManager
from database.managers.user_manager import UserManager
from database.models.user import User

from services.error_handler_service import handle_api_errors

from schemas.chat import ChatPreview
from schemas.message import ChatHistoryResponse
from schemas.message import MessageSearchRequest
from schemas.message import MessageSearchResponse

message_router = APIRouter(prefix="/messages", tags=["Сообщения"])

message_manager = MessageManager()
user_manager = UserManager()
chat_manager = ChatManager()

@message_router.get("/chats",
                    summary="Получить все чаты",
                    status_code=status.HTTP_200_OK,
                    responses=get_chats_responses,
                    description=get_chats_description)
@handle_api_errors("Ошибка при получении чатов")
async def get_chats(user: User = Depends(get_current_user)) -> List[ChatPreview]:

    chats = await chat_manager.get_user_chats_with_last_messages(user.id)
    
    chats_out = []
    for chat in chats:
        chats_out.append(ChatPreview(
            chat_id=chat.get('chat_id'),
            companion_id=chat.get('companion_id'),
            companion_login=chat.get('companion_login'),
            companion_avatar_url=chat.get('companion_avatar_url'),
            title=chat.get('title'),
            last_message=chat.get('last_message', ''),
            last_message_time=chat.get('last_message_time', datetime.datetime.now()),
            from_me=chat.get('from_me', False),
            is_read=chat.get('is_read', False)
        ))
    
    app_logger.info_event("chats_fetched", user_id=user.id, chats=len(chats_out))
    return chats_out

@message_router.get('/history/chat/{chat_id}', summary='История сообщений чата')
@handle_api_errors("Ошибка при получении истории чата")
async def get_chat_history(chat_id: int,
                           pagination: tuple[int, int] = Depends(get_large_pagination),
                           user: User = Depends(get_current_user)) -> ChatHistoryResponse:
    skip, limit = pagination
    if not await chat_manager.is_participant(chat_id, user.id):
        from fastapi import HTTPException
        raise HTTPException(status_code=403, detail="Доступ запрещен")
    
    app_logger.info(f"История для чата {chat_id}, user_id={user.id}, skip={skip}, limit={limit}")
    return await message_manager.get_chat_history_with_avatar(chat_id,
                                                              me_user_id=user.id,
                                                              skip=skip,
                                                              limit=limit)

@message_router.post("/search",
                    summary="Поиск по сообщениям",
                    status_code=status.HTTP_200_OK,
                    responses=search_messages_responses,
                    description=search_messages_description)
@handle_api_errors("Ошибка при поиске сообщений")
async def search_messages(search_request: MessageSearchRequest,
                         user: User = Depends(get_current_user)) -> MessageSearchResponse:
    """Поиск по сообщениям с фильтрацией."""
    
    # Валидация запроса
    if len(search_request.query.strip()) < 1:
        from fastapi import HTTPException
        raise HTTPException(status_code=400, detail="Поисковый запрос не может быть пустым")
    
    # Если указан chat_id, проверяем права доступа
    if search_request.chat_id:
        if not await chat_manager.is_participant(search_request.chat_id, user.id):
            from fastapi import HTTPException
            raise HTTPException(status_code=403, detail="Доступ к чату запрещен")
    
    app_logger.info(f"Поиск сообщений: query='{search_request.query}', user_id={user.id}, chat_id={search_request.chat_id}")
    
    result = await message_manager.search_messages(search_request, user.id)
    
    app_logger.info(f"Найдено {result.total_count} сообщений для пользователя {user.id}")
    return result
