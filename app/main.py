import asyncio

from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.router import main_router
from core.config import settings
from core.error_middleware import ErrorHandlerMiddleware
from database.config import engine
from database.init_db import init_db
from database.managers.connection_singleton import ensure_db_loaded
from services.score_service import periodic_recompute_task

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    
    await ensure_db_loaded()
    
    interval = getattr(settings, 'score_refresh_seconds', 300)
    app.state.score_task = asyncio.create_task(periodic_recompute_task(interval))
    yield

    task = getattr(app.state, 'score_task', None)
    if task is not None:
        task.cancel()
        try:
            await task
        except Exception:
            pass
    await engine.dispose()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan
)

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
    max_age=86400,
)

app.add_middleware(ErrorHandlerMiddleware)
app.include_router(router=main_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name}
