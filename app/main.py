from contextlib import asynccontextmanager

from api.router import main_router
from core.config import settings
from core.error_middleware import ErrorHandlerMiddleware
from database.config import engine
from database.init_db import init_db
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from services.score_service import periodic_recompute_task
import asyncio
from core.logger import app_logger


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    # Start periodic score recompute task
    interval = getattr(settings, 'score_refresh_seconds', 300)
    app.state.score_task = asyncio.create_task(periodic_recompute_task(interval))
    yield
    # Stop periodic task
    task = getattr(app.state, 'score_task', None)
    if task is not None:
        task.cancel()
        try:
            await task
        except Exception:  # noqa: BLE001
            pass
    await engine.dispose()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan
)

# CORS middleware должен быть ПЕРВЫМ!
app.add_middleware(
    CORSMiddleware,
    allow_origin_regex=settings.cors_allow_origin_regex,
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH", "HEAD"],
    allow_headers=[
        "Accept",
        "Accept-Language", 
        "Content-Language",
        "Content-Type",
        "Authorization",
        "X-Requested-With",
        "Origin",
        "Cache-Control",
        "Pragma"
    ],
    expose_headers=["*"],
    max_age=86400,  # Cache preflight для 24 часов
)

# Middleware для логирования CORS запросов - ПОСЛЕ CORS
@app.middleware("http")
async def log_cors_requests(request: Request, call_next):
    # Логируем OPTIONS запросы (CORS preflight)
    if request.method == "OPTIONS":
        origin = request.headers.get("origin", "неизвестен")
        user_agent = request.headers.get("user-agent", "неизвестен")
        app_logger.info(f"CORS preflight запрос: {request.method} {request.url} от origin: {origin}, User-Agent: {user_agent}")
    
    # Логируем наличие cookies в запросе (для отладки авторизации)
    if "/auth/" in str(request.url) and request.method in ["POST", "GET"]:
        cookies = dict(request.cookies)
        has_access = "access_token" in cookies
        has_refresh = "refresh_token" in cookies
        app_logger.info(f"Auth запрос {request.method} {request.url}: access_token={has_access}, refresh_token={has_refresh}")
    
    response = await call_next(request)
    
    # Логируем ответ для OPTIONS запросов
    if request.method == "OPTIONS":
        app_logger.info(f"CORS preflight ответ: статус {response.status_code}")
        
    return response

app.add_middleware(ErrorHandlerMiddleware)

app.include_router(router=main_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name}
