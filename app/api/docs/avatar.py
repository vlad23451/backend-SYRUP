from fastapi import status

avatar_get_responses = {
    status.HTTP_200_OK: {
        "description": "Временная ссылка на аватар успешно сгенерирована",
        "content": {
            "application/json": {
                "example": {
                    "url": "https://s3.ru-7.storage.selcloud.ru/test-backet-syrup/avatars/cbff3388-5c25-45c4-b6ca-9fa4f372aca1.jpg?AWSAccessKeyId=..."
                }
            }
        }
    },
    status.HTTP_404_NOT_FOUND: {
        "description": "Пользователь или аватар не найден",
        "content": {
            "application/json": {
                "example": {"detail": "У пользователя нет аватара"}
            }
        }
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "description": "Сервис хранилища недоступен",
        "content": {
            "application/json": {
                "example": {"detail": "Сервис хранилища недоступен"}
            }
        }
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Внутренняя ошибка сервера",
        "content": {
            "application/json": {
                "example": {"detail": "Внутренняя ошибка сервера"}
            }
        }
    }
}

avatar_upload_responses = {
    status.HTTP_200_OK: {
        "description": "Аватар успешно загружен",
        "content": {
            "application/json": {
                "example": {
                    "avatar_key": "avatars/cbff3388-5c25-45c4-b6ca-9fa4f372aca1.jpg",
                    "url": "https://s3.ru-7.storage.selcloud.ru/test-backet-syrup/avatars/cbff3388-5c25-45c4-b6ca-9fa4f372aca1.jpg?AWSAccessKeyId=..."
                }
            }
        }
    },
    status.HTTP_400_BAD_REQUEST: {
        "description": "Ошибка валидации файла",
        "content": {
            "application/json": {
                "examples": {
                    "file_too_large": {
                        "summary": "Файл слишком большой",
                        "value": {"detail": "Файл слишком большой. Максимальный размер: 10 МБ"}
                    },
                    "invalid_file_type": {
                        "summary": "Неподдерживаемый тип файла",
                        "value": {"detail": "Аватар должен быть изображением (JPEG, PNG, GIF или WebP)"}
                    },
                    "unsupported_format": {
                        "summary": "Неподдерживаемый формат",
                        "value": {"detail": "Неподдерживаемый тип файла. Разрешенные типы: image/jpeg, image/png, image/gif, image/webp"}
                    }
                }
            }
        }
    },
    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE: {
        "description": "Файл слишком большой",
        "content": {
            "application/json": {
                "example": {"detail": "Файл слишком большой. Максимальный размер: 10 МБ"}
            }
        }
    },
    status.HTTP_503_SERVICE_UNAVAILABLE: {
        "description": "Сервис хранилища недоступен",
        "content": {
            "application/json": {
                "examples": {
                    "s3_unavailable": {
                        "summary": "S3 недоступен",
                        "value": {"detail": "Не удалось подключиться к хранилищу"}
                    },
                    "upload_failed": {
                        "summary": "Ошибка загрузки",
                        "value": {"detail": "Ошибка загрузки файла"}
                    }
                }
            }
        }
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Внутренняя ошибка сервера",
        "content": {
            "application/json": {
                "example": {"detail": "Внутренняя ошибка сервера"}
            }
        }
    }
}

get_user_avatar_description = (
    "Получает временную ссылку на аватар пользователя по его ID. "
    "Ссылка действительна в течение 1 часа (по умолчанию). "
    "Требует авторизации. "
    "Возможные ошибки: пользователь не найден, у пользователя нет аватара, "
    "сервис хранилища недоступен, ошибка базы данных."
)

get_my_avatar_description = (
    "Получает временную ссылку на свой аватар. "
    "Ссылка действительна в течение 1 часа (по умолчанию). "
    "Требует авторизации. "
    "Возможные ошибки: у пользователя нет аватара, "
    "сервис хранилища недоступен."
)

upload_my_avatar_description = (
    "Загружает новый аватар для текущего пользователя. "
    "Автоматически удаляет предыдущий аватар, если он существовал. "
    "Поддерживаемые форматы: JPEG, PNG, GIF, WebP. "
    "Максимальный размер файла: 10 МБ. "
    "Генерирует уникальное имя файла и сохраняет в папку 'avatars/'. "
    "Возвращает ключ файла и временную ссылку для просмотра. "
    "Требует авторизации. "
    "Возможные ошибки: файл слишком большой, неподдерживаемый формат, "
    "сервис хранилища недоступен, ошибка валидации."
)
