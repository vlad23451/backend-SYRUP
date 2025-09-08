from fastapi import HTTPException
from fastapi import status

class MediaFileNotFoundError(HTTPException):
    def __init__(self, detail: str = "Медиа файл не найден"):
        super().__init__(status_code=status.HTTP_404_NOT_FOUND, detail=detail)

class MediaFileAccessDeniedError(HTTPException):
    def __init__(self, detail: str = "У вас нет прав доступа к этому файлу"):
        super().__init__(status_code=status.HTTP_403_FORBIDDEN, detail=detail)

class MediaFileUploadError(HTTPException):
    def __init__(self, detail: str = "Ошибка загрузки файла"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

class MediaFileValidationError(HTTPException):
    def __init__(self, detail: str = "Ошибка валидации файла"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class MediaFileTypeNotSupportedError(HTTPException):
    def __init__(self, detail: str = "Неподдерживаемый тип файла"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class MediaFileSizeExceededError(HTTPException):
    def __init__(self, detail: str = "Размер файла превышает допустимый"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)

class MediaFileOperationError(HTTPException):
    def __init__(self, detail: str = "Ошибка операции с файлом"):
        super().__init__(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=detail)

class MediaFileHistoryAttachError(HTTPException):
    def __init__(self, detail: str = "Ошибка прикрепления файла к истории"):
        super().__init__(status_code=status.HTTP_400_BAD_REQUEST, detail=detail)
