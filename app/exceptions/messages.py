from fastapi import HTTPException
from fastapi import status

class MessageNotFoundError(HTTPException):
    def __init__(self, detail: str = "Сообщение не найдено"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class OwnershipMessageError(HTTPException):
    def __init__(self, detail: str = "У вас нет прав на удаление этого сообщения"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
