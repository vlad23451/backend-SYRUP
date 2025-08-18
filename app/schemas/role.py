from enum import Enum
from pydantic import BaseModel


class UserRole(Enum):
    """Роли пользователей в системе"""
    USER = 1        # Обычный пользователь
    MODERATOR = 2   # Модератор
    ADMIN = 3       # Администратор
    
    @classmethod
    def get_role_name(cls, role_id: int) -> str:
        """Получить название роли по ID"""
        role_map = {
            1: "Пользователь",
            2: "Модератор", 
            3: "Администратор"
        }
        return role_map.get(role_id, "Неизвестная роль")
    
    @classmethod
    def get_all_roles(cls) -> dict[int, str]:
        """Получить все доступные роли"""
        return {
            1: "Пользователь",
            2: "Модератор",
            3: "Администратор"
        }
    
    @classmethod
    def has_permission(cls, user_role: int, required_role: int) -> bool:
        """Проверить, имеет ли пользователь необходимые права"""
        return user_role >= required_role


class RoleOut(BaseModel):
    """Схема вывода информации о роли"""
    id: int
    name: str
    description: str | None = None


class RoleUpdate(BaseModel):
    """Схема для обновления роли пользователя"""
    user_id: int
    new_role: int
    
    class Config:
        json_schema_extra = {
            "example": {
                "user_id": 1,
                "new_role": 2
            }
        }
