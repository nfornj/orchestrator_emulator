"""
API interface for the Specialty orchestrator module.
"""
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_dependency
from app.orchestrators.modules.specialty.schema import SpecialtyRequest, SpecialtyResponse
from app.orchestrators.modules.specialty.crud import process_specialty_request

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/specialty", tags=["specialty"])


@router.post("/", response_model=SpecialtyResponse)
async def process_specialty(
    request: SpecialtyRequest,
    db: AsyncSession = Depends(get_db_dependency)
):
    """
    Process a specialty request.
    
    Args:
        request: The specialty request
        db: Database session
        
    Returns:
        The specialty response
    """
    try:
        # Convert Pydantic model to dict
        payload = [request.model_dump()]
        
        # Process the request
        result = await process_specialty_request(payload, db=db)
        
        # Convert to response model
        response = SpecialtyResponse(
            scenario_id=request.scenario_id,
            business_type_id=request.business_type_id,
            status="success",
            results=result
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error processing specialty request: {str(e)}")
        # Return error response
        return SpecialtyResponse(
            scenario_id=request.scenario_id,
            business_type_id=request.business_type_id,
            status="error",
            error=str(e)
        )
