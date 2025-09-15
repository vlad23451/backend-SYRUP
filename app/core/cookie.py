from fastapi import Response

from api.auth_config import JWT_ACCESS_COOKIE_NAME, JWT_REFRESH_COOKIE_NAME
from api.auth_config import JWT_REFRESH_COOKIE_NAME

def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    max_age = 3600 * 24 * 7
    
    # Для HTTPS туннелей (loca.lt) нужен samesite='none' для cross-origin запросов
    response.set_cookie(JWT_ACCESS_COOKIE_NAME, 
                        access_token, 
                        httponly=True,
                        secure=True,  # Обязательно True для HTTPS
                        samesite='none',  # Разрешает cross-origin для туннелей
                        max_age=max_age)
                        
    response.set_cookie(JWT_REFRESH_COOKIE_NAME, 
                        refresh_token, 
                        httponly=True,
                        secure=True,  # Обязательно True для HTTPS
                        samesite='none',  # Разрешает cross-origin для туннелей
                        max_age=max_age)


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(JWT_ACCESS_COOKIE_NAME, 
                          secure=True,
                          samesite='none')
    response.delete_cookie(JWT_REFRESH_COOKIE_NAME, 
                          secure=True,
                          samesite='none')
