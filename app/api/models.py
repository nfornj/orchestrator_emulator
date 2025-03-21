from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class ComputeItem(BaseModel):
    scenario_id: str
    business_type_id: str
    revenue: Dict[str, Any]
    rebate: Dict[str, Any]
    speciality: Dict[str, Any]

class TaskPayload(BaseModel):
    task_name: str
    task_description: str
    app_id: int
    compute: List[ComputeItem]

class TaskResponse(BaseModel):
    task_id: str

class TaskStatus(BaseModel):
    task_id: str
    status: str
    compute_statuses: Optional[List[Dict[str, Any]]] = None 