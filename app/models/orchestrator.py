from typing import List, Dict, Any, Optional, Union
from uuid import UUID
from enum import Enum
from pydantic import BaseModel, Field, model_validator, ConfigDict
import uuid


class ComputationInput(BaseModel):
    """Base model for computation inputs with required scenario_id and business_type_id"""
    scenario_id: UUID = Field(..., description="Unique identifier for the scenario")
    business_type_id: UUID = Field(..., description="Unique identifier for the business type")
    # Additional fields can be added by inheriting models


class RevenueInput(BaseModel):
    """Model for revenue calculation input"""
    scenario_id: Union[str, uuid.UUID] = Field(..., description="The scenario ID")
    business_type_id: Union[str, uuid.UUID] = Field(..., description="The business type ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scenario_id": "123e4567-e89b-12d3-a456-426614174000",
                "business_type_id": "123e4567-e89b-12d3-a456-426614174001"
            }
        }
    )


class RebatesInput(BaseModel):
    """Model for rebates calculation input"""
    scenario_id: Union[str, uuid.UUID] = Field(..., description="The scenario ID")
    business_type_id: Union[str, uuid.UUID] = Field(..., description="The business type ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scenario_id": "123e4567-e89b-12d3-a456-426614174000",
                "business_type_id": "123e4567-e89b-12d3-a456-426614174001"
            }
        }
    )


class SpecialtyInput(BaseModel):
    """Model for specialty calculation input"""
    scenario_id: Union[str, uuid.UUID] = Field(..., description="The scenario ID")
    business_type_id: Union[str, uuid.UUID] = Field(..., description="The business type ID")

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "scenario_id": "123e4567-e89b-12d3-a456-426614174000",
                "business_type_id": "123e4567-e89b-12d3-a456-426614174001"
            }
        }
    )


class PayloadItem(BaseModel):
    """Model for a single payload item containing various service inputs"""
    revenue: Optional[RevenueInput] = Field(None, description="Revenue calculation input")
    rebates: Optional[RebatesInput] = Field(None, description="Rebates calculation input")
    specialty: Optional[SpecialtyInput] = Field(None, description="Specialty calculation input")

    @model_validator(mode='after')
    def validate_at_least_one_service(self):
        """Validate that at least one service input is provided"""
        if not (self.revenue or self.rebates or self.specialty):
            raise ValueError("At least one of revenue, rebates, or specialty must be provided")
        return self


class OrchestratorRequest(BaseModel):
    """Model for the incoming orchestrator request"""
    task_name: str = Field(..., description="Name of the task to be processed")
    task_description: str = Field(..., description="Description of the task")
    payload: List[PayloadItem] = Field(..., description="Array of computation inputs")


class ServiceResponse(BaseModel):
    """Model for service response"""
    status: str = Field(..., description="Status of the service call")
    data: List[Dict[str, Any]] = Field(..., description="Response data from the service")


class OrchestratorResponse(BaseModel):
    """Model for the orchestrator response"""
    task_id: str = Field(..., description="ID of the processed task")
    status: str = Field(..., description="Status of the orchestration request")
    results: Dict[str, Any] = Field({}, description="Results from successful service calls")
    errors: Dict[str, str] = Field({}, description="Errors from failed service calls") 