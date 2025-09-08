from __future__ import annotations

from typing import Any
from typing import Dict
from typing import List

from pydantic import BaseModel
from pydantic import ValidationError

from core.logger import app_logger
from exceptions.base import ValidationError as AppValidationError

class ValidationService:
    @staticmethod
    def validate_model_data(model: BaseModel, data: Dict[str, Any]) -> BaseModel:
        """Валидация данных модели"""
        try:
            return model.model_validate(data)
        except ValidationError as e:
            app_logger.warning(f"Ошибка валидации модели {model.__name__}: {e}")
            raise AppValidationError(f"Ошибка валидации данных: {e}")

    @staticmethod
    def validate_required_fields(data: Dict[str, Any], required_fields: List[str]) -> None:
        """Проверка обязательных полей"""
        missing_fields = [field for field in required_fields if field not in data or data[field] is None]
        if missing_fields:
            error_msg = f"Отсутствуют обязательные поля: {', '.join(missing_fields)}"
            app_logger.warning(f"Ошибка валидации: {error_msg}")
            raise AppValidationError(error_msg)

    @staticmethod
    def validate_field_type(value: Any, expected_type: type, field_name: str) -> None:
        """Проверка типа поля"""
        if not isinstance(value, expected_type):
            error_msg = f"Поле {field_name} должно быть типа {expected_type.__name__}, получено {type(value).__name__}"
            app_logger.warning(f"Ошибка валидации типа: {error_msg}")
            raise AppValidationError(error_msg)

    @staticmethod
    def validate_string_length(value: str,
                               field_name: str,
                               min_length: int = 0,
                               max_length: int | None = None) -> None:
        """Проверка длины строки"""
        if len(value) < min_length:
            error_msg = f"Поле {field_name} должно содержать минимум {min_length} символов"
            app_logger.warning(f"Ошибка валидации длины: {error_msg}")
            raise AppValidationError(error_msg)
        
        if max_length and len(value) > max_length:
            error_msg = f"Поле {field_name} должно содержать максимум {max_length} символов"
            app_logger.warning(f"Ошибка валидации длины: {error_msg}")
            raise AppValidationError(error_msg)

    @staticmethod
    def validate_numeric_range(value: int,
                               field_name: str,
                               min_value: int | None = None,
                               max_value: int | None = None) -> None:
        """Проверка числового диапазона"""
        if min_value is not None and value < min_value:
            error_msg = f"Поле {field_name} должно быть не меньше {min_value}"
            app_logger.warning(f"Ошибка валидации диапазона: {error_msg}")
            raise AppValidationError(error_msg)
        
        if max_value is not None and value > max_value:
            error_msg = f"Поле {field_name} должно быть не больше {max_value}"
            app_logger.warning(f"Ошибка валидации диапазона: {error_msg}")
            raise AppValidationError(error_msg)

    @staticmethod
    def validate_enum_value(value: Any, enum_class: type, field_name: str) -> None:
        """Проверка значения перечисления"""
        valid_values = [e.value for e in enum_class]
        if value not in valid_values:
            error_msg = f"Поле {field_name} должно быть одним из значений: {', '.join(map(str, valid_values))}"
            app_logger.warning(f"Ошибка валидации enum: {error_msg}")
            raise AppValidationError(error_msg)

    @staticmethod
    def sanitize_string(value: str) -> str:
        """Очистка строки от потенциально опасных символов"""
        return value.strip()
