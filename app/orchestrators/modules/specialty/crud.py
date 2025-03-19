"""
CRUD operations for the Specialty orchestrator module.
"""
import logging
import httpx
from typing import Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_tracking import ServiceRequest, ServiceStatus
from app.services.task_tracking import TaskTrackingService
from app.orchestrators.modules.specialty.schema import SpecialtyRequest, SpecialtyResponse

# Configure logging
logger = logging.getLogger(__name__)

# Configuration - can be overridden with environment variables
SPECIALTY_SERVICE_URL = "http://specialty-service:8003/specialty"
HTTP_TIMEOUT = 30  # seconds


async def process_specialty_request(
    payload: List[Dict[str, Any]], 
    service_request_id: int = None,
    db: AsyncSession = None,
    service_url: str = SPECIALTY_SERVICE_URL,
    timeout: int = HTTP_TIMEOUT
) -> Dict[str, Any]:
    """
    Process specialty service requests.
    
    Args:
        payload: The specialty service payload
        service_request_id: The ID of the service request in the database
        db: Database session
        service_url: URL of the specialty service
        timeout: HTTP timeout in seconds
        
    Returns:
        The response from the specialty service
    """
    try:
        logger.info(f"Processing specialty request with {len(payload)} items")
        
        # Make an async HTTP request to the service
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(
                service_url,
                json=payload,
                headers={"Content-Type": "application/json"}
            )
            
            # Check for successful response
            response.raise_for_status()
            
            # Parse the response
            result = response.json()
            
            # Update service request status if available
            if db and service_request_id:
                await TaskTrackingService.update_service_status(
                    db, 
                    service_request_id,
                    ServiceStatus.COMPLETED,
                    response_payload=result
                )
            
            return result
            
    except httpx.RequestError as e:
        logger.error(f"Request error calling specialty service: {str(e)}")
        # Update service request status if available
        if db and service_request_id:
            await TaskTrackingService.update_service_status(
                db, 
                service_request_id,
                ServiceStatus.FAILED,
                error_message=f"Request error: {str(e)}"
            )
        raise
    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error calling specialty service: {str(e)}")
        # Update service request status if available
        if db and service_request_id:
            await TaskTrackingService.update_service_status(
                db, 
                service_request_id,
                ServiceStatus.FAILED,
                error_message=f"HTTP error: {str(e)}"
            )
        raise
    except Exception as e:
        logger.error(f"Unexpected error calling specialty service: {str(e)}")
        # Update service request status if available
        if db and service_request_id:
            await TaskTrackingService.update_service_status(
                db, 
                service_request_id,
                ServiceStatus.FAILED,
                error_message=f"Unexpected error: {str(e)}"
            )
        raise
