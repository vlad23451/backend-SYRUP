from typing import List

from fastapi import APIRouter
from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from api.dependencies.role import require_admin
from api.dependencies.role import get_user_permissions
from api.docs.role import get_available_roles_description
from api.docs.role import available_roles_responses
from api.docs.role import get_my_permissions_description
from api.docs.role import permissions_responses
from api.docs.role import update_user_role_description
from api.docs.role import update_role_responses
from api.docs.role import get_users_by_role_description
from api.docs.role import users_by_role_responses
from api.docs.role import get_role_statistics_description
from api.docs.role import statistics_responses

from core.logger import app_logger

from database.managers.user_manager import UserManager
from database.models.user import User

from schemas.role import RoleOut
from schemas.role import RoleUpdate
from schemas.role import UserRole
from schemas.user import UserOut

from services.error_handler_service import handle_api_errors

role_router = APIRouter(prefix='/roles', tags=['Роли пользователей'])

user_manager = UserManager()

@role_router.get('/available',
                 summary='Получить все доступные роли',
                 status_code=status.HTTP_200_OK,
                 response_model=List[RoleOut],
                 responses=available_roles_responses,
                 description=get_available_roles_description)
async def get_available_roles() -> List[RoleOut]:
    """Получить список всех доступных ролей в системе."""
    roles = []
    for role_id, role_name in UserRole.get_all_roles().items():
        description = {
            1: "Обычный пользователь с базовыми правами",
            2: "Модератор с правами управления контентом",
            3: "Администратор с полными правами"
        }.get(role_id, "")
        
        roles.append(RoleOut(
            id=role_id,
            name=role_name,
            description=description
        ))
    
    return roles

@role_router.get('/my-permissions',
                 summary='Получить мои права доступа',
                 status_code=status.HTTP_200_OK,
                 responses=permissions_responses,
                 description=get_my_permissions_description)
async def get_my_permissions(permissions: dict = Depends(get_user_permissions)) -> dict:
    """Получить информацию о правах текущего пользователя."""
    return permissions

@role_router.put('/update-user-role',
                 summary='Изменить роль пользователя',
                 status_code=status.HTTP_200_OK,
                 response_model=UserOut,
                 responses=update_role_responses,
                 description=update_user_role_description)
@handle_api_errors("Ошибка при изменении роли пользователя")
async def update_user_role(
    role_update: RoleUpdate,
    admin_user: User = Depends(require_admin)
) -> UserOut:
    """
    Изменить роль пользователя. Доступно только администраторам.
    
    - **user_id**: ID пользователя для изменения роли
    - **new_role**: Новая роль (1=USER, 2=MODERATOR, 3=ADMIN)
    """
    # Проверяем, что новая роль валидна
    if role_update.new_role not in UserRole.get_all_roles():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Указана недопустимая роль"
        )
    
    # Проверяем, что пользователь существует
    target_user = await user_manager.get_obj_by_id(role_update.user_id)
    if not target_user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Пользователь не найден"
        )
    
    # Запрещаем администратору изменять собственную роль
    if admin_user.id == role_update.user_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Нельзя изменить собственную роль"
        )
    
    # Обновляем роль
    old_role = target_user.role
    await user_manager.update_obj(
        id=role_update.user_id,
        updated_obj={"role": role_update.new_role}
    )
    
    # Получаем обновленного пользователя
    updated_user = await user_manager.get_obj_by_id(role_update.user_id)
    
    # Логируем изменение роли
    app_logger.info(
        f"Администратор {admin_user.login} (ID: {admin_user.id}) изменил роль пользователя "
        f"{updated_user.login} (ID: {updated_user.id}) с {UserRole.get_role_name(old_role)} "
        f"на {UserRole.get_role_name(role_update.new_role)}"
    )
    
    # Получаем обновленного пользователя с отношениями
    updated_user_with_relations = await user_manager.get_user_by_id_with_relations(updated_user.id)
    from services.avatar_service import avatar_service
    user_out = await UserOut.from_user_with_relations(updated_user_with_relations, avatar_service)
    
    return user_out

@role_router.get('/users-by-role/{role_id}',
                 summary='Получить пользователей по роли',
                 status_code=status.HTTP_200_OK,
                 response_model=List[UserOut],
                 responses=users_by_role_responses,
                 description=get_users_by_role_description)
@handle_api_errors("Ошибка при получении пользователей по роли")
async def get_users_by_role(
    role_id: int,
    admin_user: User = Depends(require_admin)
) -> List[UserOut]:
    """
    Получить список пользователей с определенной ролью.
    Доступно только администраторам.
    """
    if role_id not in UserRole.get_all_roles():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Указана недопустимая роль"
        )
    
    users = await user_manager.get_users_by_role_with_relations(role_id)
    
    # Создаем UserOut с отношениями
    from services.avatar_service import avatar_service
    result = []
    for user in users:
        user_out = await UserOut.from_user_with_relations(user, avatar_service)
        result.append(user_out)
    
    return result

@role_router.get('/statistics',
                 summary='Статистика по ролям',
                 status_code=status.HTTP_200_OK,
                 responses=statistics_responses,
                 description=get_role_statistics_description)
@handle_api_errors("Ошибка при получении статистики по ролям")
async def get_role_statistics(
    admin_user: User = Depends(require_admin)
) -> dict:
    """
    Получить статистику распределения ролей.
    Доступно только администраторам.
    """
    stats = await user_manager.get_role_statistics()
    
    # Добавляем названия ролей в статистику
    result = {}
    for role_id, count in stats.items():
        role_name = UserRole.get_role_name(role_id)
        result[f"{role_name} (ID: {role_id})"] = count
    
    return {
        "total_users": sum(stats.values()),
        "roles_distribution": result
    }
