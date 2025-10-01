from fastapi import APIRouter
from fastapi import Depends
from fastapi import Query
from fastapi import status
from fastapi import HTTPException

from api.dependencies.auth import get_current_user
from api.docs.pinned_message import (
    pin_message_responses,
    unpin_message_responses,
    get_pinned_messages_responses,
    pin_message_description,
    unpin_message_description,
    get_pinned_messages_description
)

from core.logger import app_logger

from database.managers.pinned_message_manager import PinnedMessageManager
from database.managers.chat_manager import ChatManager
from database.models.user import User

from services.error_handler_service import handle_api_errors

from schemas.pinned_message import (
    PinMessageRequest,
    UnpinMessageRequest,
    PinnedMessageListResponse,
    PinnedMessageOut
)

pinned_message_router = APIRouter(prefix="/pinned-messages", tags=["Закрепленные сообщения"])

pinned_message_manager = PinnedMessageManager()
chat_manager = ChatManager()

@pinned_message_router.post("/pin",
                           summary="Закрепить сообщение",
                           status_code=status.HTTP_201_CREATED,
                           responses=pin_message_responses,
                           description=pin_message_description)
@handle_api_errors("Ошибка при закреплении сообщения")
async def pin_message(pin_request: PinMessageRequest,
                     chat_id: int = Query(..., description="ID чата"),
                     user: User = Depends(get_current_user)) -> PinnedMessageOut:
    if not await chat_manager.is_participant(chat_id, user.id):
        raise HTTPException(status_code=403, detail="Доступ к чату запрещен")
    
    try:
        pinned_message = await pinned_message_manager.pin_message(
            message_id=pin_request.message_id,
            chat_id=chat_id,
            user_id=user.id
        )
        
        app_logger.info(f"Сообщение {pin_request.message_id} закреплено в чате {chat_id} пользователем {user.id}")
        
        return PinnedMessageOut(
            id=pinned_message.id,
            message_id=pinned_message.message_id,
            chat_id=pinned_message.chat_id,
            pinned_by_user_id=pinned_message.pinned_by_user_id,
            pinned_at=pinned_message.pinned_at
        )
        
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))

@pinned_message_router.delete("/unpin",
                             summary="Открепить сообщение",
                             status_code=status.HTTP_200_OK,
                             responses=unpin_message_responses,
                             description=unpin_message_description)
@handle_api_errors("Ошибка при откреплении сообщения")
async def unpin_message(unpin_request: UnpinMessageRequest,
                       chat_id: int = Query(..., description="ID чата"),
                       user: User = Depends(get_current_user)) -> dict:
    if not await chat_manager.is_participant(chat_id, user.id):
        raise HTTPException(status_code=403, detail="Доступ к чату запрещен")
    
    success = await pinned_message_manager.unpin_message(
        message_id=unpin_request.message_id,
        chat_id=chat_id,
        user_id=user.id
    )
    
    if not success:
        raise HTTPException(status_code=404, detail="Закрепленное сообщение не найдено")
    
    app_logger.info(f"Сообщение {unpin_request.message_id} откреплено в чате {chat_id} пользователем {user.id}")
    
    return {"message": "Сообщение успешно откреплено"}

@pinned_message_router.get("/chat/{chat_id}",
                          summary="Получить закрепленные сообщения чата",
                          status_code=status.HTTP_200_OK,
                          responses=get_pinned_messages_responses,
                          description=get_pinned_messages_description)
@handle_api_errors("Ошибка при получении закрепленных сообщений")
async def get_pinned_messages(chat_id: int,
                             skip: int = Query(0, ge=0, description="Смещение для пагинации"),
                             limit: int = Query(50, ge=1, le=100, description="Количество сообщений"),
                             user: User = Depends(get_current_user)) -> PinnedMessageListResponse:
    if not await chat_manager.is_participant(chat_id, user.id):
        raise HTTPException(status_code=403, detail="Доступ к чату запрещен")
    
    result = await pinned_message_manager.get_pinned_messages(
        chat_id=chat_id,
        user_id=user.id,
        skip=skip,
        limit=limit
    )
    
    app_logger.info(f"Получены закрепленные сообщения чата {chat_id} для пользователя {user.id}")
    return result


@pinned_message_router.get("/check/{message_id}",
                          summary="Проверить, закреплено ли сообщение",
                          status_code=status.HTTP_200_OK)
@handle_api_errors("Ошибка при проверке статуса закрепления")
async def check_message_pinned(message_id: int,
                              chat_id: int = Query(..., description="ID чата"),
                              user: User = Depends(get_current_user)) -> dict:
    if not await chat_manager.is_participant(chat_id, user.id):
        raise HTTPException(status_code=403, detail="Доступ к чату запрещен")
    
    is_pinned = await pinned_message_manager.is_message_pinned(message_id, chat_id)
    
    return {
        "message_id": message_id,
        "chat_id": chat_id,
        "is_pinned": is_pinned
    }
