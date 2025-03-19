from typing import List, Optional, Dict, Any
import uuid
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.task_tracking import Task, ServiceRequest, TaskStatus, ServiceStatus
from app.schemas.task_tracking import TaskCreate, ServiceRequestCreate, TaskResponse, ServiceRequestResponse
from app.utils import to_json

class TaskTrackingService:
    @staticmethod
    async def create_task(db: AsyncSession, task_data: TaskCreate) -> Task:
        """Create a new task in the database."""
        # Generate a new UUID if not provided
        task_id = str(uuid.uuid4())
        
        # Create a new Task instance
        task = Task(
            task_id=task_id,
            task_name=task_data.task_name,
            task_description=task_data.task_description,
            status=TaskStatus.PENDING,
            payload=task_data.payload
        )
        
        db.add(task)
        await db.commit()
        await db.refresh(task)
        return task
    
    @staticmethod
    async def add_service_request(db: AsyncSession, task_id: str, service_data: ServiceRequestCreate) -> ServiceRequest:
        """Add a new service request to an existing task."""
        service_request = ServiceRequest(
            task_id=task_id,
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
    
    @staticmethod
    async def get_task_by_id(db: AsyncSession, task_id: str) -> Optional[TaskResponse]:
        """Get a task by its ID."""
        try:
            # Execute the query
            result = await db.execute(select(Task).where(Task.task_id == task_id))
            
            # Get the task
            task = result.scalars().first()
            
            if not task:
                return None
                
            # Load related service requests
            await db.refresh(task, ["service_requests"])
                
            # Convert service requests to Pydantic models
            service_request_responses = []
            for sr in task.service_requests:
                sr_response = ServiceRequestResponse(
                    id=sr.id,
                    task_id=sr.task_id,
                    service_name=sr.service_name,
                    scenario_id=sr.scenario_id,
                    business_type_id=sr.business_type_id,
                    status=sr.status.name if hasattr(sr.status, 'name') else sr.status,
                    created_at=sr.created_at,
                    updated_at=sr.updated_at,
                    request_payload=sr.request_payload,
                    response_payload=sr.response_payload,
                    error_message=sr.error_message
                )
                service_request_responses.append(sr_response)
            
            # Convert to TaskResponse model
            task_response = TaskResponse(
                id=task.id,
                task_id=task.task_id,
                task_name=task.task_name,
                task_description=task.task_description,
                status=task.status.name if hasattr(task.status, 'name') else task.status,
                created_at=task.created_at,
                updated_at=task.updated_at,
                payload=task.payload,
                error_message=task.error_message,
                service_requests=service_request_responses
            )
            
            return task_response
        except Exception as e:
            # Log the error
            import logging
            logging.error(f"Error in get_task_by_id: {str(e)}")
            raise
    
    @staticmethod
    async def update_task_status(db: AsyncSession, task_id: str, status: TaskStatus, error_message: Optional[str] = None) -> Optional[TaskResponse]:
        """Update the status of a task."""
        # Query the task directly from the database
        result = await db.execute(select(Task).where(Task.task_id == task_id))
        task_db = result.scalars().first()
        
        if task_db:
            task_db.status = status
            if error_message:
                task_db.error_message = error_message
            await db.commit()
            await db.refresh(task_db)
            
            # Get the updated task using get_task_by_id to convert to TaskResponse
            return await TaskTrackingService.get_task_by_id(db, task_id)
        
        return None
    
    @staticmethod
    async def update_service_status(
        db: AsyncSession, 
        service_id: int, 
        status: ServiceStatus, 
        response_payload: Optional[Dict[str, Any]] = None,
        error_message: Optional[str] = None
    ) -> Optional[ServiceRequest]:
        """Update the status of a service request."""
        result = await db.execute(select(ServiceRequest).where(ServiceRequest.id == service_id))
        service_request = result.scalars().first()
        
        if service_request:
            service_request.status = status
            if response_payload:
                service_request.response_payload = response_payload
            if error_message:
                service_request.error_message = error_message
            await db.commit()
            await db.refresh(service_request)
            
            # After updating a service, check if all services for this task are complete
            # If so, update the task status to COMPLETED
            await TaskTrackingService._check_and_update_task_status(db, service_request.task_id)
            
        return service_request
    
    @staticmethod
    async def _check_and_update_task_status(db: AsyncSession, task_id: str) -> None:
        """Check if all services for a task are complete and update task status accordingly."""
        # Get all service requests for this task
        result = await db.execute(
            select(ServiceRequest).where(ServiceRequest.task_id == task_id)
        )
        service_requests = result.scalars().all()
        
        # Check if all services are completed or if any have failed
        all_completed = all(sr.status == ServiceStatus.COMPLETED for sr in service_requests)
        any_failed = any(sr.status == ServiceStatus.FAILED for sr in service_requests)
        
        if service_requests and all_completed:
            await TaskTrackingService.update_task_status(db, task_id, TaskStatus.COMPLETED)
        elif any_failed:
            await TaskTrackingService.update_task_status(db, task_id, TaskStatus.FAILED)
    
    @staticmethod
    async def get_all_tasks(db: AsyncSession) -> List[TaskResponse]:
        """Get all tasks from the database."""
        try:
            # Execute the query
            result = await db.execute(select(Task).order_by(Task.created_at.desc()))
            
            # Get all tasks
            tasks = result.scalars().all()
            
            # Convert SQLAlchemy objects to Pydantic models
            task_responses = []
            for task in tasks:
                # Load related service requests
                await db.refresh(task, ["service_requests"])
                
                # Convert to TaskResponse model
                task_response = TaskResponse(
                    id=task.id,
                    task_id=task.task_id,
                    task_name=task.task_name,
                    task_description=task.task_description,
                    status=task.status.name if hasattr(task.status, 'name') else task.status,
                    created_at=task.created_at,
                    updated_at=task.updated_at,
                    payload=task.payload,
                    error_message=task.error_message,
                    service_requests=[]  # Will populate separately if needed
                )
                
                task_responses.append(task_response)
            
            return task_responses
        except Exception as e:
            # Log the error
            import logging
            logging.error(f"Error in get_all_tasks: {str(e)}")
            raise 