from typing import List, Dict, Any, Optional
from datetime import datetime
import uuid
from pydantic import BaseModel, Field

class ServiceRequestCreate(BaseModel):
    service_name: str
    scenario_id: Optional[str] = None
    business_type_id: Optional[str] = None
    request_payload: Optional[Dict[str, Any]] = None
    
class ServiceRequestResponse(BaseModel):
    id: uuid.UUID
    task_id: uuid.UUID
    service_name: str
    scenario_id: Optional[str] = None
    business_type_id: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    request_payload: Optional[Dict[str, Any]] = None
    response_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    
    class Config:
        from_attributes = True

class TaskCreate(BaseModel):
    task_name: str
    task_description: Optional[str] = None
    payload: Optional[List[Dict[str, Any]]] = None
    
class TaskResponse(BaseModel):
    id: uuid.UUID
    task_id: str
    task_name: str
    task_description: Optional[str] = None
    status: str
    created_at: datetime
    updated_at: datetime
    payload: Optional[List[Dict[str, Any]]] = None
    error_message: Optional[str] = None
    service_requests: List[ServiceRequestResponse] = []
    
    class Config:
        from_attributes = True

class TaskStatusUpdate(BaseModel):
    status: str
    error_message: Optional[str] = None
    
class ServiceStatusUpdate(BaseModel):
    status: str
    response_payload: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None 