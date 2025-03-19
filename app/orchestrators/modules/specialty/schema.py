"""
Schema definitions for the Specialty orchestrator module.
"""
from typing import Dict, Any, Optional, List
from pydantic import BaseModel, Field
import uuid


class SpecialtyRequest(BaseModel):
    """Specialty service request schema."""
    scenario_id: uuid.UUID = Field(..., description="The scenario ID to process")
    business_type_id: uuid.UUID = Field(..., description="The business type ID")
    
    class Config:
        json_encoders = {uuid.UUID: str}


class SpecialtyResponse(BaseModel):
    """Specialty service response schema."""
    scenario_id: uuid.UUID
    business_type_id: uuid.UUID
    status: str
    results: Optional[Dict[str, Any]] = None
    error: Optional[str] = None
    
    class Config:
        json_encoders = {uuid.UUID: str}
