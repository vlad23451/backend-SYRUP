from fastapi import APIRouter, Depends, Query
from api.dependencies.auth import get_current_user
from database.models.user import User
from services.online_status_service import OnlineStatusService
from services.error_handler_service import handle_api_errors

online_status_router = APIRouter(prefix="/online-status", tags=["Статус онлайн"])
online_status_service = OnlineStatusService()

@online_status_router.get("/{user_id}")
@handle_api_errors("Ошибка при получении статуса пользователя")
async def get_user_online_status(user_id: int, user: User = Depends(get_current_user)):
    """Получить статус онлайн пользователя"""
    return await online_status_service.get_online_status(user_id)

@online_status_router.get("/")
@handle_api_errors("Ошибка при получении статусов пользователей")
async def get_multiple_online_status(
    user_ids: str = Query(..., description="ID пользователей через запятую"),
    user: User = Depends(get_current_user)
):
    """Получить статусы нескольких пользователей"""
    try:
        ids = [int(id.strip()) for id in user_ids.split(",")]
        return await online_status_service.get_multiple_online_status(ids)
    except ValueError:
        return {"error": "Неверный формат ID пользователей"}

@online_status_router.get("/debug/connections")
@handle_api_errors("Ошибка при получении информации о соединениях")
async def get_debug_connections(user: User = Depends(get_current_user)):
    """Получить отладочную информацию о WebSocket соединениях"""
    from database.managers.connection_manager import get_connection_manager
    connection_manager = get_connection_manager()
    
    return {
        "active_connections": list(connection_manager.active_connections.keys()),
        "online_users": list(online_status_service.online_users),
        "total_connections": len(connection_manager.active_connections)
    }
