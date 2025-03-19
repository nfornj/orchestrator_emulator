import asyncio
import json
import logging
import uuid
from typing import Dict, Any, List, Optional

import httpx
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import OrchestratorRequest, ServiceResponse
from app.models.task_tracking import TaskStatus, ServiceStatus, Task, ServiceRequest
from app.services.task_tracking import TaskTrackingService
from app.schemas.task_tracking import ServiceRequestCreate
from app.utils import to_json, JSONEncoder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuration - can be overridden with environment variables
REVENUE_SERVICE_URL = "http://revenue-service:8001/revenue"
REBATES_SERVICE_URL = "http://rebates-service:8002/rebates"
SPECIALTY_SERVICE_URL = "http://specialty-service:8003/specialty"
HTTP_TIMEOUT = 30  # seconds


class OrchestratorService:
    """
    Service that orchestrates the processing of payloads by splitting them
    and making asynchronous calls to external services.
    """
    
    def __init__(
        self,
        revenue_url: str = REVENUE_SERVICE_URL,
        rebates_url: str = REBATES_SERVICE_URL,
        specialty_url: str = SPECIALTY_SERVICE_URL,
        timeout: int = HTTP_TIMEOUT
    ):
        """
        Initialize the OrchestratorService.
        
        Args:
            revenue_url: URL for the revenue service
            rebates_url: URL for the rebates service
            specialty_url: URL for the specialty service
            timeout: Timeout for HTTP requests in seconds
        """
        self.revenue_url = revenue_url
        self.rebates_url = rebates_url
        self.specialty_url = specialty_url
        self.timeout = timeout
        self.db_session = None
    
    async def process_request(self, request_data: Dict[str, Any], db: AsyncSession = None) -> Dict[str, Any]:
        """
        Process an orchestrator request by splitting the payload and calling external services.
        
        Args:
            request_data: The request data to process
            db: The database session for task tracking
            
        Returns:
            A dictionary with the response data
        """
        # Use task_id from request if available, otherwise generate a new one
        task_id = request_data.get("task_id", str(uuid.uuid4()))
        logger.info(f"Processing request with task_id: {task_id}")
        
        self.db_session = db
        
        try:
            # Validate the request using Pydantic
            request = OrchestratorRequest.model_validate(request_data)
            
            # Update task status to in progress if DB session is available
            if db:
                await TaskTrackingService.update_task_status(db, task_id, TaskStatus.IN_PROGRESS)
            
            # Process the payload
            results = {}
            errors = {}
            
            # Extract items for each service type
            revenue_items = []
            rebates_items = []
            specialty_items = []
            
            for item in request.payload:
                if item.revenue:
                    revenue_items.append(item.revenue.model_dump())
                if item.rebates:
                    rebates_items.append(item.rebates.model_dump())
                if item.specialty:
                    specialty_items.append(item.specialty.model_dump())
            
            # Create service requests in database if available
            service_requests = {}
            if db:
                if revenue_items:
                    revenue_request = await self._create_service_request(db, task_id, "revenue", revenue_items)
                    service_requests["revenue"] = revenue_request
                
                if rebates_items:
                    rebates_request = await self._create_service_request(db, task_id, "rebates", rebates_items)
                    service_requests["rebates"] = rebates_request
                
                if specialty_items:
                    specialty_request = await self._create_service_request(db, task_id, "specialty", specialty_items)
                    service_requests["specialty"] = specialty_request
            
            # Call the services asynchronously
            calls = []
            
            if revenue_items:
                calls.append(self._call_service(self.revenue_url, revenue_items, "revenue"))
            
            if rebates_items:
                calls.append(self._call_service(self.rebates_url, rebates_items, "rebates"))
            
            if specialty_items:
                calls.append(self._call_service(self.specialty_url, specialty_items, "specialty"))
            
            # Wait for all services to complete
            if calls:
                service_results = await asyncio.gather(*calls, return_exceptions=True)
                
                # Process results
                for service_name, service_result in service_results:
                    if isinstance(service_result, Exception):
                        errors[service_name] = str(service_result)
                        logger.error(f"Error calling {service_name} service: {str(service_result)}")
                        
                        # Update service status to failed if DB session is available
                        if db and service_name in service_requests:
                            await TaskTrackingService.update_service_status(
                                db, 
                                service_requests[service_name].id,
                                ServiceStatus.FAILED,
                                error_message=str(service_result)
                            )
                    else:
                        results[service_name] = service_result
                        logger.info(f"Successfully processed {service_name} service call")
                        
                        # Update service status to completed if DB session is available
                        if db and service_name in service_requests:
                            await TaskTrackingService.update_service_status(
                                db, 
                                service_requests[service_name].id,
                                ServiceStatus.COMPLETED,
                                response_payload=service_result
                            )
            
            # Determine task status
            task_status = "success" if not errors else "partial_success" if results else "failure"
            
            # Update task status if DB session is available
            if db:
                db_status = TaskStatus.COMPLETED if task_status == "success" else TaskStatus.FAILED
                error_message = to_json(errors) if errors else None
                await TaskTrackingService.update_task_status(db, task_id, db_status, error_message)
            
            # Return the combined results
            return {
                "task_id": task_id,
                "status": task_status,
                "results": results,
                "errors": errors
            }
            
        except ValidationError as e:
            logger.error(f"Validation error: {str(e)}")
            
            # Update task status to failed if DB session is available
            if db:
                await TaskTrackingService.update_task_status(
                    db, task_id, TaskStatus.FAILED, 
                    error_message=f"Validation error: {str(e)}"
                )
            
            return {
                "task_id": task_id,
                "status": "failure",
                "results": {},
                "errors": {"validation": str(e)}
            }
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            
            # Update task status to failed if DB session is available
            if db:
                await TaskTrackingService.update_task_status(
                    db, task_id, TaskStatus.FAILED, 
                    error_message=f"Unexpected error: {str(e)}"
                )
            
            return {
                "task_id": task_id,
                "status": "failure",
                "results": {},
                "errors": {"unexpected": str(e)}
            }
    
    async def _create_service_request(self, db: AsyncSession, task_id: str, service_name: str, payload: List[Dict]) -> Any:
        """
        Create a service request in the database.
        
        Args:
            db: The database session
            task_id: The task ID
            service_name: The name of the service
            payload: The service payload
            
        Returns:
            The created service request
        """
        # Default values for scenario_id and business_type_id
        scenario_id = str(uuid.uuid4())
        business_type_id = str(uuid.uuid4())
        
        # Extract scenario_id and business_type_id from the first payload item if available
        try:
            if payload and isinstance(payload, list) and len(payload) > 0:
                first_item = payload[0]
                
                # Check which service we're creating a request for
                service_key = service_name.lower()
                if service_key in first_item and first_item[service_key]:
                    service_data = first_item[service_key]
                    if "scenario_id" in service_data:
                        scenario_id = service_data["scenario_id"]
                    if "business_type_id" in service_data:
                        business_type_id = service_data["business_type_id"]
        except Exception as e:
            logger.warning(f"Error extracting scenario/business type IDs: {str(e)}")
        
        # Look up the task by task_id to get its database ID
        result = await db.execute(select(Task).where(Task.task_id == task_id))
        task = result.scalars().first()
        
        if not task:
            logger.error(f"Task with ID {task_id} not found when creating service request")
            raise ValueError(f"Task with ID {task_id} not found")
            
        # Create the service request with the task's actual ID
        service_data = ServiceRequestCreate(
            service_name=service_name,
            scenario_id=scenario_id,
            business_type_id=business_type_id,
            request_payload={"items": payload} if payload else {}
        )
        
        # Create and return the service request
        service_request = ServiceRequest(
            task_id=task.id,  # Use the UUID from the database
            service_name=service_data.service_name,
            scenario_id=service_data.scenario_id,
            business_type_id=service_data.business_type_id,
            status=ServiceStatus.PENDING,
            request_payload=service_data.request_payload
        )
        
        db.add(service_request)
        await db.commit()
        await db.refresh(service_request)
        return service_request
    
    async def _call_service(self, url: str, payload: List[Dict[str, Any]], service_name: str) -> tuple:
        """
        Call an external service with the given payload.
        
        Args:
            url: The URL of the service to call
            payload: The payload to send
            service_name: The name of the service for logging
            
        Returns:
            A tuple of (service_name, result)
        """
        try:
            # Make an async HTTP request to the service
            logger.info(f"Calling {service_name} service with {len(payload)} items")
            
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"}
                )
                
                # Check for successful response
                response.raise_for_status()
                
                # Parse the response
                result = response.json()
                
                # Validate with Pydantic model (if needed)
                # service_response = ServiceResponse.model_validate(result)
                
                return service_name, result
                
        except httpx.RequestError as e:
            logger.error(f"Request error calling {service_name} service: {str(e)}")
            return service_name, e
        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error calling {service_name} service: {str(e)}")
            return service_name, e
        except Exception as e:
            logger.error(f"Unexpected error calling {service_name} service: {str(e)}")
            return service_name, e 