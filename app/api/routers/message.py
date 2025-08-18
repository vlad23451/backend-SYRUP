import datetime
from typing import List

from api.dependencies.auth import get_current_user
from api.docs.message import get_chats_description, get_chats_responses
from core.logger import app_logger
from database.managers.message_manager import MessageManager
from database.managers.user_manager import UserManager
from database.models.user import User
from exceptions.users import UserNotFoundError
from fastapi import APIRouter, Depends, status
from schemas.chat import ChatOut
from services.error_handler_service import handle_api_errors
from fastapi import Query
from schemas.message import MessageOut

message_router = APIRouter(prefix="/messages", tags=["Сообщения"])

message_manager = MessageManager()
user_manager = UserManager()

@message_router.get("/chats",
                    summary="Получить все чаты",
                    status_code=status.HTTP_200_OK,
                    responses=get_chats_responses,
                    description=get_chats_description)
@handle_api_errors("Ошибка при получении чатов")
async def get_chats(user: User = Depends(get_current_user)) -> List[ChatOut]:
    user_id = getattr(user, 'id', 0)
    if not user:
        raise UserNotFoundError()
    room_ids = await message_manager.get_room_ids_by_user_id(getattr(user, 'id', 0))

    companion_ids = []
    last_messages = []

    for room_id in room_ids:
        last_msg = await message_manager.get_last_message_by_room_id(room_id)
        companion_ids.append(last_msg.sender_id if last_msg.sender_id != user_id else last_msg.receiver_id)
        last_messages.append(last_msg)

    companions = [await user_manager.get_obj_by_id(uid) for uid in companion_ids]

    chats_out = []

    for i, comp in enumerate(companions):
        last_msg = last_messages[i]
        chats_out.append(ChatOut(
            companion_id=int(getattr(comp, 'id', 0)),
            companion_login=str(comp.login),
            companion_avatar_url=str(comp.avatar_key) if comp.avatar_key is not None else None,
            last_message=str(getattr(last_msg, 'text', None)),
            last_message_time=getattr(last_msg, 'timestamp', datetime.datetime.now()),
            from_me=bool(getattr(last_msg, 'sender_id', 0) == user_id),
            room_id=getattr(last_msg, 'room_id', None),
            is_read=False
        ))
    app_logger.info_event("chats_fetched", user_id=user.id, chats=len(chats_out))
    return chats_out


@message_router.get('/history/room/{room_id}', summary='История сообщений комнаты')
@handle_api_errors("Ошибка при получении истории комнаты")
async def get_room_history(room_id: str,
                           skip: int = Query(0, ge=0),
                           limit: int = Query(50, ge=1, le=200),
                           user: User = Depends(get_current_user)) -> List[MessageOut]:
    app_logger.info(f"История для комнаты {room_id}, user_id={user.id}, skip={skip}, limit={limit}")
    return await message_manager.get_history_by_room(room_id, me_user_id=user.id, skip=skip, limit=limit)


@message_router.get('/history/with/{companion_id}', summary='История сообщений с пользователем')
@handle_api_errors("Ошибка при получении истории с пользователем")
async def get_history_with_user(companion_id: int,
                                skip: int = Query(0, ge=0),
                                limit: int = Query(50, ge=1, le=200),
                                user: User = Depends(get_current_user)) -> List[MessageOut]:
    app_logger.info(f"История с пользователем {companion_id}, user_id={user.id}, skip={skip}, limit={limit}")
    # Нормализованный room_id здесь не обязателен — выбираем по паре участников
    return await message_manager.get_history_with_user(user1_id=user.id, user2_id=companion_id, me_user_id=user.id, skip=skip, limit=limit)
