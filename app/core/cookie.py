from api.auth_config import JWT_ACCESS_COOKIE_NAME, JWT_REFRESH_COOKIE_NAME
from fastapi import Response


def set_auth_cookies(response: Response, access_token: str, refresh_token: str) -> None:
    max_age = 3600 * 24 * 7
    
    response.set_cookie(JWT_ACCESS_COOKIE_NAME, 
                        access_token, 
                        httponly=False,
                        secure=False,
                        samesite='lax',
                        max_age=max_age)
                        
    response.set_cookie(JWT_REFRESH_COOKIE_NAME, 
                        refresh_token, 
                        httponly=False,
                        secure=False,
                        samesite='lax',
                        max_age=max_age)


def clear_auth_cookies(response: Response) -> None:
    response.delete_cookie(JWT_ACCESS_COOKIE_NAME)
    response.delete_cookie(JWT_REFRESH_COOKIE_NAME)
