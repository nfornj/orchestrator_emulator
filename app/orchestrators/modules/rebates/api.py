"""
API interface for the Rebates orchestrator module.
"""
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_dependency
from app.orchestrators.modules.rebates.schema import RebatesRequest, RebatesResponse
from app.orchestrators.modules.rebates.crud import process_rebates_request

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/rebates", tags=["rebates"])


@router.post("/", response_model=RebatesResponse)
async def process_rebates(
    request: RebatesRequest,
    db: AsyncSession = Depends(get_db_dependency)
):
    """
    Process a rebates request.
    
    Args:
        request: The rebates request
        db: Database session
        
    Returns:
        The rebates response
    """
    try:
        # Convert Pydantic model to dict
        payload = [request.model_dump()]
        
        # Process the request
        result = await process_rebates_request(payload, db=db)
        
        # Convert to response model
        response = RebatesResponse(
            scenario_id=request.scenario_id,
            business_type_id=request.business_type_id,
            status="success",
            results=result
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error processing rebates request: {str(e)}")
        # Return error response
        return RebatesResponse(
            scenario_id=request.scenario_id,
            business_type_id=request.business_type_id,
            status="error",
            error=str(e)
        )
