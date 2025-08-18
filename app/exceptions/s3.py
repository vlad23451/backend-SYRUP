"""Исключения для работы с S3."""

from fastapi import HTTPException, status


class S3ObjectNotFoundError(HTTPException):
    def __init__(self, detail: str = "Файл не найден в хранилище"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


class S3ServiceUnavailableError(HTTPException):
    def __init__(self, detail: str = "Сервис хранилища недоступен"):
        super().__init__(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail=detail)


class S3UploadError(HTTPException):
    def __init__(self, detail: str = "Ошибка загрузки файла"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)


class S3ValidationError(HTTPException):
    def __init__(self, detail: str = "Ошибка валидации файла"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
