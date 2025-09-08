import json
from datetime import datetime
from typing import Any
from typing import Dict

def datetime_serializer(obj: Any) -> str:
    if isinstance(obj, datetime):
        return obj.isoformat()
    raise TypeError(f"Object of type {type(obj)} is not JSON serializable")

def safe_json_dumps(data: Any) -> str:
    """Безопасная сериализация в JSON с поддержкой datetime."""
    return json.dumps(data, default=datetime_serializer)

def safe_json_loads(json_str: str) -> Any:
    """Безопасная десериализация из JSON."""
    return json.loads(json_str)

def prepare_for_websocket(data: Dict[str, Any]) -> Dict[str, Any]:
    """Подготовка данных для отправки через WebSocket."""
    try:
        json.dumps(data)
        return data
    except (TypeError, ValueError):
        return json.loads(safe_json_dumps(data))
