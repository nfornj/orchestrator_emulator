"""
API interface for the Revenue orchestrator module.
"""
import logging
from typing import Dict, Any, List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db_dependency
from app.orchestrators.modules.revenue.schema import RevenueRequest, RevenueResponse
from app.orchestrators.modules.revenue.crud import process_revenue_request

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/revenue", tags=["revenue"])


@router.post("/", response_model=RevenueResponse)
async def process_revenue(
    request: RevenueRequest,
    db: AsyncSession = Depends(get_db_dependency)
):
    """
    Process a revenue request.
    
    Args:
        request: The revenue request
        db: Database session
        
    Returns:
        The revenue response
    """
    try:
        # Convert Pydantic model to dict
        payload = [request.model_dump()]
        
        # Process the request
        result = await process_revenue_request(payload, db=db)
        
        # Convert to response model
        response = RevenueResponse(
            scenario_id=request.scenario_id,
            business_type_id=request.business_type_id,
            status="success",
            results=result
        )
        
        return response
    
    except Exception as e:
        logger.error(f"Error processing revenue request: {str(e)}")
        # Return error response
        return RevenueResponse(
            scenario_id=request.scenario_id,
            business_type_id=request.business_type_id,
            status="error",
            error=str(e)
        )
