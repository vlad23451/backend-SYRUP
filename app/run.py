import uvicorn
from core.config import settings

if __name__ == '__main__':
    uvicorn.run(
        'main:app',
        host=settings.host,
        port=settings.port,
        reload=True,
        log_level="info" if not settings.debug else "debug"
    )
