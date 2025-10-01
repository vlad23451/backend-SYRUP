from fastapi import HTTPException
from fastapi import status

class UserBlockNotFoundError(HTTPException):
    def __init__(self, message: str = "Блокировка пользователя не найдена"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)

class UserSelfBlockError(HTTPException):
    def __init__(self, message: str = "Нельзя заблокировать самого себя"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=message)

class UserAlreadyBlockedError(HTTPException):
    def __init__(self, message: str = "Пользователь уже заблокирован"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=message)
