from fastapi import HTTPException, status


class CommentNotFoundError(HTTPException):
    def __init__(self, detail: str = "Комментарий не найден"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class OwnershipCommentError(HTTPException):
    def __init__(self, detail: str = "У вас нет прав на изменение или удаление этого комментария"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail) 
