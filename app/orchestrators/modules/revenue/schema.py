"""
Schema definitions for the Revenue orchestrator module.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import uuid


class RevenueRequest(BaseModel):
    """Revenue service request schema."""
    scenario_id: uuid.UUID = Field(..., description="The scenario ID to process")
    business_type_id: uuid.UUID = Field(..., description="The business type ID")
    
    class Config:
        json_encoders = {uuid.UUID: str}


class RevenueResponse(BaseModel):
    """Revenue service response schema."""
    scenario_id: uuid.UUID
    business_type_id: uuid.UUID
    status: str
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    class Config:
        json_encoders = {uuid.UUID: str}
