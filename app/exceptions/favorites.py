from fastapi import HTTPException
from fastapi import status

class FavoriteNotFoundError(HTTPException):
    def __init__(self, detail: str = "История не найдена в избранном"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class FavoriteAlreadyExistsError(HTTPException):
    def __init__(self, detail: str = "История уже добавлена в избранное"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)

class OwnershipFavoriteError(HTTPException):
    def __init__(self, detail: str = "У вас нет прав на управление этим избранным"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)
