from fastapi import HTTPException
from fastapi import status

class HistoryViewNotFoundError(HTTPException):
    def __init__(self, message: str = "Просмотр истории не найден"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=message)

class HistoryViewAlreadyExistsError(HTTPException):
    def __init__(self, message: str = "Просмотр уже существует"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=message)
