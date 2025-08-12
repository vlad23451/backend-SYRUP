from fastapi import status

follower_create_responses = {
    status.HTTP_201_CREATED: {
        "description": "Подписка оформлена.",
        "content": {"application/json": {"example": {"user_id": 1, "follower_id": 2}}}
    },
    status.HTTP_404_NOT_FOUND: {
        "description": "Пользователь не найден (UserNotFoundError)",
        "content": {"application/json": {"example": {"detail": "Пользователь не найден."}}}
    },
    status.HTTP_409_CONFLICT: {
        "description": "Подписка уже существует.",
        "content": {"application/json": {"example": {"detail": "Подписка уже существует."}}}
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Внутренняя ошибка сервера (DatabaseError)",
        "content": {"application/json": {"example": {"detail": "Внутренняя ошибка сервера."}}}
    },
}

follower_delete_responses = {
    status.HTTP_204_NO_CONTENT: {"description": "Подписка удалена."},
    status.HTTP_404_NOT_FOUND: {
        "description": "Подписка не найдена.",
        "content": {"application/json": {"example": {"detail": "Подписка не найдена."}}}
    },
    status.HTTP_500_INTERNAL_SERVER_ERROR: {
        "description": "Внутренняя ошибка сервера (DatabaseError)",
        "content": {"application/json": {"example": {"detail": "Внутренняя ошибка сервера."}}}
    },
}

follower_get_responses = {
    status.HTTP_200_OK: {
        "description": "Список подписчиков/подписок пользователя.",
        "content": {"application/json": {"example": [{"user_id": 1, "follower_id": 2}]}}
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

follow_description = (
    "Создаёт подписку на пользователя по его идентификатору. "
    "Если подписка становится взаимной, пользователи автоматически становятся друзьями. "
    "Требует авторизации. "
    "Возвращает объект подписки с датой создания. "
    "Возможные ошибки: пользователь не найден, подписка уже существует, ошибка базы данных."
)

unfollow_description = (
    "Удаляет подписку на пользователя по его идентификатору. "
    "Если пользователи были друзьями, дружба также удаляется. "
    "Требует авторизации. "
    "Возвращает статус 204 при успешном удалении. "
    "Возможные ошибки: подписка не найдена, ошибка базы данных."
)

get_followers_description = (
    "Возвращает список подписчиков пользователя по его идентификатору. "
    "Каждый элемент содержит информацию о подписчике. "
    "Возможные ошибки: пользователь не найден, ошибка базы данных."
)

get_following_description = (
    "Возвращает список пользователей, на которых подписан текущий пользователь. "
    "Требует авторизации. "
    "Каждый элемент содержит информацию о подписке. "
    "Возможные ошибки: ошибка базы данных."
) 
