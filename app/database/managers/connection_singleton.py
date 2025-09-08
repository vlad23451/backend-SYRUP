import asyncio

from database.managers.connection_manager import ConnectionManager

_connection_manager_instance = None
_db_load_task = None

def get_connection_manager() -> ConnectionManager:
    global _connection_manager_instance, _db_load_task
    if _connection_manager_instance is None:
        _connection_manager_instance = ConnectionManager()
        
        # Запускаем загрузку данных из БД в фоновом режиме
        if _db_load_task is None:
            _db_load_task = asyncio.create_task(_load_db_data())
    
    return _connection_manager_instance

async def _load_db_data():
    """Загрузить данные из БД в фоновом режиме."""
    global _connection_manager_instance
    if _connection_manager_instance:
        await _connection_manager_instance.load_chat_participants_from_db()

async def ensure_db_loaded():
    """Убедиться, что данные из БД загружены (для использования в lifespan)."""
    global _db_load_task
    if _db_load_task:
        await _db_load_task
