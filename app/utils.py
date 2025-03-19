import json
import uuid
from datetime import datetime
from typing import Any

class JSONEncoder(json.JSONEncoder):
    """
    Custom JSON encoder that handles UUID, datetime, and other special types.
    """
    def default(self, obj: Any) -> Any:
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, datetime):
            return obj.isoformat()
        return super().default(obj)

def to_json(obj: Any) -> str:
    """
    Convert an object to a JSON string with proper serialization of UUID types.
    
    Args:
        obj: The object to convert to JSON
        
    Returns:
        A JSON string
    """
    return json.dumps(obj, cls=JSONEncoder)

def parse_json(json_str: str) -> Any:
    """
    Parse a JSON string into an object.
    
    Args:
        json_str: The JSON string to parse
        
    Returns:
        The parsed object
    """
    if not json_str:
        return None
    return json.loads(json_str) 