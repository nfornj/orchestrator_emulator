import json
import logging
import uuid
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Custom JSON encoder for UUID objects
class UUIDEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        return super().default(obj)

class EventHub:
    """Simple implementation of an event hub for testing."""
    
    @staticmethod
    def to_json(data: Any) -> str:
        """Convert data to JSON string with proper UUID handling."""
        return json.dumps(data, cls=UUIDEncoder)
    
    @staticmethod
    def from_json(json_str: str) -> Any:
        """Parse JSON string to Python object."""
        return json.loads(json_str)
    
    @staticmethod
    def serialize_event(event_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Serialize event data, handling UUID objects properly.
        
        Args:
            event_data: The event data to serialize
            
        Returns:
            Serialized event data safe for JSON conversion
        """
        # First convert to JSON string with custom encoder
        json_str = EventHub.to_json(event_data)
        
        # Then convert back to dict to create a copy with UUID properly serialized
        return json.loads(json_str) 