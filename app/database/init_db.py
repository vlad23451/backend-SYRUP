from core.logger import app_logger
from database.config import Base, engine


async def init_db():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    app_logger.info(f"База данных инициализирована")
