from fastapi import HTTPException
from fastapi import status

class LikeNotFoundError(HTTPException):
    def __init__(self, detail: str = "Лайк не найден"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class OwnershipLikeError(HTTPException):
    def __init__(self, detail: str = "У вас нет прав на удаление этого лайка"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class DislikeNotFoundError(HTTPException):
    def __init__(self, detail: str = "Дизлайк не найден"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class OwnershipDislikeError(HTTPException):
    def __init__(self, detail: str = "У вас нет прав на удаление этого дизлайка"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class CommentLikeNotFoundError(HTTPException):
    def __init__(self, detail: str = "Лайк комментария не найден"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class OwnershipCommentLikeError(HTTPException):
    def __init__(self, detail: str = "У вас нет прав на удаление этого лайка комментария"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class CommentDislikeNotFoundError(HTTPException):
    def __init__(self, detail: str = "Дизлайк комментария не найден"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class OwnershipCommentDislikeError(HTTPException):
    def __init__(self, detail: str = "У вас нет прав на удаление этого дизлайка комментария"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail) 
