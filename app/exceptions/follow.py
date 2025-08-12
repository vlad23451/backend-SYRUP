from fastapi import HTTPException, status


class FollowAlredyExists(HTTPException):
    def __init__(self, detail: str = "Вы уже подписаны"):
        super().__init__(status_code=status.HTTP_409_CONFLICT, detail=detail)
