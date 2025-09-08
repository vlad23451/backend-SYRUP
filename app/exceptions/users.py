from fastapi import HTTPException
from fastapi import status

class UserAlreadyExistsError(HTTPException):
    def __init__(self, detail: str = "Пользователь с таким логином уже существует"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class UserNotFoundError(HTTPException):
    def __init__(self, detail: str = "Пользователь не найден"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class InvalidCredentialsError(HTTPException):
    def __init__(self, detail: str = "Неверный логин или пароль"):
        super().__init__(status_code=status.HTTP_401_UNAUTHORIZED, detail=detail)

class InvalidUserDataError(HTTPException):
    def __init__(self, detail: str = "Неверные данные пользователя"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
