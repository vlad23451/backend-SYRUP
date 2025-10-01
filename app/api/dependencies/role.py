from fastapi import Depends
from fastapi import HTTPException
from fastapi import status

from api.dependencies.auth import get_current_user

from database.models.user import User

from exceptions.base import PermissionError

from schemas.role import UserRole

def require_role(required_role: int):
    def check_role(current_user: User = Depends(get_current_user)) -> User:
        if not UserRole.has_permission(current_user.role, required_role):
            raise PermissionError(detail=f"Доступ запрещен. Требуется роль: {UserRole.get_role_name(required_role)}")
        return current_user
    return check_role

def require_admin(current_user: User = Depends(get_current_user)) -> User:
    if current_user.role != UserRole.ADMIN.value:
        raise PermissionError(detail="Доступ запрещен. Требуются права администратора.")
    return current_user

def require_moderator_or_above(current_user: User = Depends(get_current_user)) -> User:
    if not UserRole.has_permission(current_user.role, UserRole.MODERATOR.value):
        raise PermissionError(detail="Доступ запрещен. Требуются права модератора или администратора.")
    return current_user

def check_ownership_or_moderator(target_user_id: int):
    def check_permission(current_user: User = Depends(get_current_user)) -> User:
        if current_user.id == target_user_id:
            return current_user
        
        if UserRole.has_permission(current_user.role, UserRole.MODERATOR.value):
            return current_user
            
        raise PermissionError(detail="Доступ запрещен. Недостаточно прав.")
    return check_permission

def get_user_permissions(current_user: User = Depends(get_current_user)) -> dict:
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
