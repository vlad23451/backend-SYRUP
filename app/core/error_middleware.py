"""Глобальный middleware обработки ошибок.

Конвертирует известные исключения домена в структурированные JSON-ответы,
а остальные — в 500 с логированием через `app_logger`.
"""
from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_500_INTERNAL_SERVER_ERROR

from core.logger import app_logger

from exceptions.base import DatabaseError
from exceptions.base import PermissionError
from exceptions.base import UnknownDatabaseError
from exceptions.base import ValidationError

from exceptions.comments import CommentNotFoundError
from exceptions.comments import OwnershipCommentError

from exceptions.histories import HistoryNotFoundError
from exceptions.histories import OwnershipHistoryError

from exceptions.likes import LikeNotFoundError
from exceptions.likes import OwnershipLikeError

from exceptions.messages import MessageNotFoundError
from exceptions.messages import OwnershipMessageError

from exceptions.users import InvalidCredentialsError
from exceptions.users import InvalidUserDataError
from exceptions.users import UserAlreadyExistsError
from exceptions.users import UserNotFoundError

class ErrorHandlerMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        try:
            response = await call_next(request)
            return response
        except (
            ValidationError, PermissionError, DatabaseError, UnknownDatabaseError,
            UserNotFoundError, UserAlreadyExistsError, InvalidCredentialsError, InvalidUserDataError,
            CommentNotFoundError, OwnershipCommentError,
            HistoryNotFoundError, OwnershipHistoryError,
            LikeNotFoundError, OwnershipLikeError,
            MessageNotFoundError, OwnershipMessageError
        ) as exc:
            return JSONResponse(
                status_code=exc.status_code,
                content={
                    "error": exc.detail,
                    "status_code": exc.status_code
                }
            )
        except Exception as exc:
            app_logger.error_event(
                "unhandled_exception",
                path=str(request.url.path),
                method=request.method,
                client=str(request.client.host) if request.client else None,
                error=str(exc.__class__.__name__),
            )
            return JSONResponse(
                status_code=HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "error": "Внутренняя ошибка сервера. Попробуйте позже.",
                    "status_code": HTTP_500_INTERNAL_SERVER_ERROR
                }
            )
