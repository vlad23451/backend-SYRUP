from contextlib import asynccontextmanager

from api.router import main_router
from core.config import settings
from core.error_middleware import ErrorHandlerMiddleware
from database.config import engine
from database.init_db import init_db
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await engine.dispose()

app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(ErrorHandlerMiddleware)

app.include_router(router=main_router)

@app.get("/health")
async def health_check():
    return {"status": "healthy", "app": settings.app_name}
