from fastapi import HTTPException, status


class HistoryNotFoundError(HTTPException):
    def __init__(self, detail: str = "История не найдена"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class OwnershipHistoryError(HTTPException):
    def __init__(self, detail: str = "У вас нет прав на удаление этой истории"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
