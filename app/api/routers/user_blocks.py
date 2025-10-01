from fastapi import APIRouter
from fastapi import Depends
from fastapi import status

from api.dependencies.auth import get_current_user
from api.dependencies.pagination import get_medium_pagination

from database.managers.user_block_manager import UserBlockManager
from database.models.user import User

from exceptions.user_blocks import UserBlockNotFoundError
from exceptions.user_blocks import UserSelfBlockError
from exceptions.user_blocks import UserAlreadyBlockedError

from schemas.user_block import UserBlockCreate
from schemas.user_block import UserBlockResponse
from schemas.user_block import BlockedUsersResponse

from services.error_handler_service import handle_api_errors

from core.logger import app_logger

user_blocks_router = APIRouter(prefix='/user-blocks', tags=['Блокировка пользователей'])

user_block_manager = UserBlockManager()

@user_blocks_router.post('/',
                        summary='Заблокировать пользователя',
                        status_code=status.HTTP_201_CREATED,
                        description='Заблокировать пользователя с указанием причины.')
@handle_api_errors("Ошибка при блокировке пользователя")
async def block_user(block_data: UserBlockCreate,
                    user: User = Depends(get_current_user)) -> UserBlockResponse:
    if user.id == block_data.blocked_user_id:
        raise UserSelfBlockError()
    
    existing_block = await user_block_manager.get_block_by_users(user.id, block_data.blocked_user_id)
    if existing_block:
        raise UserAlreadyBlockedError()
    
    block = await user_block_manager.block_user(
        blocker_id=user.id,
        blocked_user_id=block_data.blocked_user_id,
        reason=block_data.reason
    )
    
    if not block:
        raise UserAlreadyBlockedError()
    
    app_logger.info_event("user_block_created", 
                         blocker_id=user.id, 
                         blocked_id=block_data.blocked_user_id)
    
    return UserBlockResponse(
        message="Пользователь успешно заблокирован",
        block=block
    )

@user_blocks_router.delete('/{blocked_user_id}',
                          summary='Разблокировать пользователя',
                          status_code=status.HTTP_200_OK,
                          description='Разблокировать пользователя.')
@handle_api_errors("Ошибка при разблокировке пользователя")
async def unblock_user(blocked_user_id: int,
                      user: User = Depends(get_current_user)) -> dict:
    success = await user_block_manager.unblock_user(user.id, blocked_user_id)
    
    if not success:
        raise UserBlockNotFoundError()
    
    app_logger.info_event("user_unblocked", 
                         blocker_id=user.id, 
                         blocked_id=blocked_user_id)
    
    return {"message": "Пользователь успешно разблокирован"}

@user_blocks_router.get('/blocked',
                       summary='Получить список заблокированных пользователей',
                       status_code=status.HTTP_200_OK,
                       description='Получить список пользователей, заблокированных текущим пользователем.')
@handle_api_errors("Ошибка при получении заблокированных пользователей")
async def get_blocked_users(user: User = Depends(get_current_user),
                           pagination: tuple[int, int] = Depends(get_medium_pagination)) -> BlockedUsersResponse:
    skip, limit = pagination
    blocks, total = await user_block_manager.get_blocked_users(
        blocker_id=user.id,
        skip=skip,
        limit=limit
    )
    
    app_logger.info_event("blocked_users_fetched", 
                         user_id=user.id, 
                         count=len(blocks),
                         total=total)
    
    return BlockedUsersResponse(
        items=blocks,
        total=total
    )

@user_blocks_router.get('/check/{user_id}',
                       summary='Проверить, заблокирован ли пользователь',
                       status_code=status.HTTP_200_OK,
                       description='Проверить, заблокирован ли указанный пользователь текущим пользователем.')
@handle_api_errors("Ошибка при проверке блокировки пользователя")
async def check_user_block(user_id: int,
                          user: User = Depends(get_current_user)) -> dict:
    is_blocked = await user_block_manager.is_user_blocked(user.id, user_id)
    
    return {
        "user_id": user_id,
        "is_blocked": is_blocked
    }

@user_blocks_router.get('/blocked-by',
                       summary='Получить список пользователей, которые заблокировали меня',
                       status_code=status.HTTP_200_OK,
                       description='Получить список пользователей, которые заблокировали текущего пользователя.')
@handle_api_errors("Ошибка при получении пользователей, которые заблокировали меня")
async def get_blocked_by_users(user: User = Depends(get_current_user),
                              pagination: tuple[int, int] = Depends(get_medium_pagination)) -> BlockedUsersResponse:
    skip, limit = pagination
    blocks, total = await user_block_manager.get_blocked_by_users_with_status(
        blocked_id=user.id,
        skip=skip,
        limit=limit
    )
    
    app_logger.info_event("blocked_by_users_fetched", 
                         user_id=user.id, 
                         count=len(blocks),
                         total=total)
    
    return BlockedUsersResponse(
        items=blocks,
        total=total
    )
