from __future__ import annotations

from functools import wraps

from typing import Awaitable
from typing import Callable
from typing import TypeVar

from core.logger import app_logger

from exceptions.all_exceptions import *

T = TypeVar('T')

class ErrorHandlerService:
    @staticmethod
    async def handle_database_operation(operation: Callable[[], Awaitable[T]], 
                                        error_message: str,
                                        log_context: str = "") -> T:
        try:
            return await operation()
        except KNOWN_EXCEPTIONS:
            raise
        except Exception as e:
            if log_context:
                app_logger.error(f"{error_message} {log_context}: {e}")
            else:
                app_logger.error(f"{error_message}: {e}")
            raise DatabaseError(error_message)

    @staticmethod
    def handle_api_operation(operation: Callable[[], T], 
                             error_message: str,
                             log_context: str = "") -> T:
        try:
            return operation()
        except KNOWN_EXCEPTIONS:
            raise
        except Exception as e:
            if log_context:
                app_logger.error(f"{error_message} {log_context}: {e}")
            else:
                app_logger.error(f"{error_message}: {e}")
            raise DatabaseError(error_message)

    @staticmethod
    def log_success_operation(operation_name: str, context: str = ""):
        if context:
            app_logger.info(f"{operation_name} {context}")
        else:
            app_logger.info(f"{operation_name}")

    @staticmethod
    def log_warning_operation(operation_name: str, context: str = ""):
        if context:
            app_logger.warning(f"{operation_name} {context}")
        else:
            app_logger.warning(f"{operation_name}")

def handle_api_errors(error_message: str):
    def decorator(func: Callable[..., Awaitable[T]]) -> Callable[..., Awaitable[T]]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            try:
                return await func(*args, **kwargs)
            except KNOWN_EXCEPTIONS:
                raise
            except Exception as e:
                app_logger.error(f"{error_message}: {e}")
                raise DatabaseError(error_message)
        return wrapper
    return decorator
