"""Зависимости для проверки ролей пользователей."""

from fastapi import Depends, HTTPException, status
from database.models.user import User
from schemas.role import UserRole
from api.dependencies.auth import get_current_user


def require_role(required_role: int):
    """
    Фабрика зависимостей для проверки роли пользователя.
    
    Args:
        required_role: Минимальная требуемая роль (1=USER, 2=MODERATOR, 3=ADMIN)
    
    Returns:
        Функция-зависимость для FastAPI
    """
    def check_role(current_user: User = Depends(get_current_user)) -> User:
        if not UserRole.has_permission(current_user.role, required_role):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Недостаточно прав. Требуется роль: {UserRole.get_role_name(required_role)}"
            )
        return current_user
    return check_role


def require_admin(current_user: User = Depends(get_current_user)) -> User:
    """Требует роль администратора."""
    if current_user.role != UserRole.ADMIN.value:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуются права администратора."
        )
    return current_user


def require_moderator_or_above(current_user: User = Depends(get_current_user)) -> User:
    """Требует роль модератора или выше."""
    if not UserRole.has_permission(current_user.role, UserRole.MODERATOR.value):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Требуются права модератора или администратора."
        )
    return current_user


def check_ownership_or_moderator(target_user_id: int):
    """
    Проверяет, что пользователь либо владелец ресурса, либо модератор/админ.
    
    Args:
        target_user_id: ID пользователя-владельца ресурса
    """
    def check_permission(current_user: User = Depends(get_current_user)) -> User:
        # Если это владелец ресурса
        if current_user.id == target_user_id:
            return current_user
        
        # Если это модератор или админ
        if UserRole.has_permission(current_user.role, UserRole.MODERATOR.value):
            return current_user
            
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Доступ запрещен. Недостаточно прав."
        )
    return check_permission


def get_user_permissions(current_user: User = Depends(get_current_user)) -> dict:
    """
    Возвращает информацию о правах текущего пользователя.
    """
    role_name = UserRole.get_role_name(current_user.role)
    
    permissions = {
        "user_id": current_user.id,
        "role": current_user.role,
        "role_name": role_name,
        "can_moderate": UserRole.has_permission(current_user.role, UserRole.MODERATOR.value),
        "can_admin": current_user.role == UserRole.ADMIN.value,
        "can_delete_others_content": UserRole.has_permission(current_user.role, UserRole.MODERATOR.value),
        "can_manage_users": current_user.role == UserRole.ADMIN.value,
    }
    
    return permissions
