from fastapi import status

media_upload_responses = {
    status.HTTP_200_OK: {
        "description": "Файл успешно загружен.",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "filename": "photo.jpg",
                    "file_key": "photos/uuid-12345.jpg",
                    "file_type": "image",
                    "mime_type": "image/jpeg",
                    "file_size": 1024000,
                    "folder": "photos",
                    "download_url": "https://s3.example.com/bucket/photos/uuid-12345.jpg",
                    "created_at": "2024-01-01T12:00:00Z"
                }
            }
        }
    },
    status.HTTP_400_BAD_REQUEST: {
        "description": "Ошибка валидации файла (MediaFileValidationError)",
        "content": {
            "application/json": {
                "example": {"detail": "Неподдерживаемое расширение файла: .exe"}
            }
        }
    },
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
        "description": "Файл слишком большой (MediaFileSizeExceededError)",
        "content": {
            "application/json": {
                "example": {"detail": "Файл слишком большой. Максимальный размер: 10MB"}
            }
        }
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Ошибка загрузки файла (MediaFileUploadError)",
        "content": {
            "application/json": {
                "example": {"detail": "Ошибка загрузки файла"}
            }
        }
    }
}

media_file_responses = {
    status.HTTP_200_OK: {
        "description": "Информация о файле.",
        "content": {
            "application/json": {
                "example": {
                    "id": 1,
                    "filename": "document.pdf",
                    "file_key": "documents/uuid-67890.pdf",
                    "file_type": "document",
                    "mime_type": "application/pdf",
                    "file_size": 2048000,
                    "folder": "documents",
                    "user_id": 123,
                    "history_id": 456,
                    "description": "Важный документ",
                    "is_public": True,
                    "download_url": "https://s3.example.com/bucket/documents/uuid-67890.pdf",
                    "created_at": "2024-01-01T10:00:00Z",
                    "updated_at": "2024-01-01T12:00:00Z"
                }
            }
        }
    },
    status.HTTP_404_NOT_FOUND: {
        "description": "Файл не найден (MediaFileNotFoundError)",
        "content": {
            "application/json": {
                "example": {"detail": "Файл не найден или у вас нет прав доступа"}
            }
        }
    },
    status.HTTP_403_FORBIDDEN: {
        "description": "Нет прав доступа (MediaFileAccessDeniedError)",
        "content": {
            "application/json": {
                "example": {"detail": "У вас нет прав доступа к этому файлу"}
            }
        }
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Ошибка операции с файлом (MediaFileOperationError)",
        "content": {
            "application/json": {
                "example": {"detail": "Ошибка операции с файлом"}
            }
        }
    }
}

media_file_list_responses = {
    status.HTTP_200_OK: {
        "description": "Список файлов с пагинацией.",
        "content": {
            "application/json": {
                "example": {
                    "files": [
                        {
                            "id": 1,
                            "filename": "photo1.jpg",
                            "file_type": "image",
                            "file_size": 1024000,
                            "created_at": "2024-01-01T12:00:00Z"
                        }
                    ],
                    "total": 25,
                    "page": 1,
                    "per_page": 50
                }
            }
        }
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Ошибка получения файлов (MediaFileOperationError)",
        "content": {
            "application/json": {
                "example": {"detail": "Ошибка получения файлов"}
            }
        }
    }
}

media_attach_responses = {
    status.HTTP_200_OK: {
        "description": "Файл успешно прикреплен/откреплен.",
        "content": {
            "application/json": {
                "example": {"message": "Файл успешно прикреплен к истории"}
            }
        }
    },
    status.HTTP_403_FORBIDDEN: {
        "description": "Нет прав на операцию (MediaFileAccessDeniedError)",
        "content": {
            "application/json": {
                "example": {"detail": "Файл не найден или у вас нет прав на его прикрепление"}
            }
        }
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Ошибка операции (MediaFileOperationError)",
        "content": {
            "application/json": {
                "example": {"detail": "Ошибка операции с файлом"}
            }
        }
    }
}

upload_file_description = (
    "Загружает файл в S3 хранилище и создает запись в базе данных. "
    "Файлы автоматически распределяются по папкам в зависимости от типа: "
    "изображения (до 10MB), видео (до 100MB), аудио (до 50MB), документы (до 20MB). "
    "Требует авторизации. "
    "Возможные ошибки: неподдерживаемый тип файла, превышение размера, ошибка загрузки."
)

get_user_files_description = (
    "Получает файлы текущего пользователя с возможностью фильтрации по типу и пагинацией. "
    "Поддерживает параметры: file_type (image/video/audio/document), limit, offset. "
    "Требует авторизации. "
    "Возможные ошибки: ошибка получения данных."
)

get_file_description = (
    "Получает информацию о конкретном файле, включая временную ссылку для скачивания. "
    "Пользователь может получить информацию только о своих файлах или публичных файлах. "
    "Требует авторизации. "
    "Возможные ошибки: файл не найден, нет прав доступа."
)

update_file_description = (
    "Обновляет описание и настройки публичности файла. "
    "Пользователь может изменять только свои файлы. "
    "Требует авторизации. "
    "Возможные ошибки: файл не найден, нет прав на изменение."
)

delete_file_description = (
    "Удаляет файл из S3 хранилища и базы данных. "
    "Пользователь может удалять только свои файлы. "
    "Требует авторизации. "
    "Возможные ошибки: файл не найден, нет прав на удаление."
)

get_history_files_description = (
    "Получает все файлы, прикрепленные к конкретной истории. "
    "Доступно без авторизации. "
    "Возможные ошибки: ошибка получения данных."
)

attach_file_description = (
    "Прикрепляет файл к истории. "
    "Пользователь может прикреплять только свои файлы. "
    "Требует авторизации. "
    "Возможные ошибки: файл не найден, нет прав на прикрепление."
)

detach_file_description = (
    "Открепляет файл от истории. "
    "Пользователь может открепляать только свои файлы. "
    "Требует авторизации. "
    "Возможные ошибки: файл не найден, нет прав на открепление."
)

get_public_files_description = (
    "Получает все публичные файлы всех пользователей с пагинацией. "
    "Доступно без авторизации. "
    "Поддерживает параметры: limit, offset для пагинации. "
    "Возможные ошибки: ошибка получения данных."
)
