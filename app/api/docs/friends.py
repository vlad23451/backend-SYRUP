from fastapi import status

friend_create_responses = {
    status.HTTP_201_CREATED: {
        "description": "Заявка в друзья отправлена.",
        "content": {"application/json": {"example": {"user_id": 1, "friend_id": 2, "status": "pending"}}}
    },
    status.HTTP_404_NOT_FOUND: {
        "description": "Пользователь не найден (UserNotFoundError)",
        "content": {"application/json": {"example": {"detail": "Пользователь не найден."}}}
    },
    status.HTTP_409_CONFLICT: {
        "description": "Заявка уже существует.",
        "content": {"application/json": {"example": {"detail": "Заявка уже существует."}}}
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Внутренняя ошибка сервера (DatabaseError)",
        "content": {"application/json": {"example": {"detail": "Внутренняя ошибка сервера."}}}
    },
}

friend_update_status_responses = {
    status.HTTP_200_OK: {
        "description": "Статус дружбы обновлён.",
        "content": {"application/json": {"example": {"user_id": 1, "friend_id": 2, "status": "accepted"}}}
    },
    status.HTTP_404_NOT_FOUND: {
        "description": "Заявка не найдена.",
        "content": {"application/json": {"example": {"detail": "Заявка не найдена."}}}
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Внутренняя ошибка сервера (DatabaseError)",
        "content": {"application/json": {"example": {"detail": "Внутренняя ошибка сервера."}}}
    },
}

friend_delete_responses = {
    status.HTTP_204_NO_CONTENT: {"description": "Дружба удалена."},
    status.HTTP_404_NOT_FOUND: {
        "description": "Заявка не найдена.",
        "content": {"application/json": {"example": {"detail": "Заявка не найдена."}}}
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Внутренняя ошибка сервера (DatabaseError)",
        "content": {"application/json": {"example": {"detail": "Внутренняя ошибка сервера."}}}
    },
}

friend_get_responses = {
    status.HTTP_200_OK: {
        "description": "Список друзей пользователя.",
        "content": {"application/json": {"example": [{"user_id": 1, "friend_id": 2, "status": "accepted"}]}}
    },
    status.HTTP_404_NOT_FOUND: {
        "description": "Пользователь не найден.",
        "content": {"application/json": {"example": {"detail": "Пользователь не найден."}}}
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Внутренняя ошибка сервера (DatabaseError)",
        "content": {"application/json": {"example": {"detail": "Внутренняя ошибка сервера."}}}
    },
}

remove_friend_description = (
    "Удаляет друга из списка друзей текущего пользователя. "
    "Требует авторизации. "
    "Если дружба не найдена, возвращает ошибку. "
    "Возможные ошибки: дружба не найдена, ошибка базы данных."
)

get_friends_description = (
    "Возвращает список всех друзей текущего пользователя. "
    "Каждый элемент содержит информацию о друге. "
    "Требует авторизации. "
    "Возможные ошибки: ошибка базы данных."
)
