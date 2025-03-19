import logging
from typing import Dict, Any, List
import uuid
import os
import json

from fastapi import APIRouter, HTTPException, BackgroundTasks, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import OrchestratorRequest, OrchestratorResponse
from app.services.orchestrator import OrchestratorService
from app.services.event_hub import EventHubProducer
from app.database import get_db_dependency, get_db
from app.services.task_tracking import TaskTrackingService
from app.models.task_tracking import TaskStatus, ServiceStatus, Task
from app.schemas.task_tracking import TaskCreate, TaskResponse, ServiceRequestCreate, ServiceRequestResponse
from app.utils import JSONEncoder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create router
router = APIRouter()

# Initialize services
orchestrator_service = OrchestratorService()

# Check if we should use Event Hub
USE_EVENT_HUB = os.environ.get("USE_EVENT_HUB", "True").lower() == "true"

async def process_task_in_background(request_data: Dict[str, Any], task_id: str):
    """
    Process a task in the background.
    
    Args:
        request_data: The request data to process
        task_id: The task ID for tracking
    """
    try:
        logger.info(f"Starting background processing for task {task_id}")
        logger.info(f"Request data: {json.dumps(request_data, cls=JSONEncoder)}")
        
        # Get a database session
        async with get_db() as db:
            # Update task status to IN_PROGRESS
            logger.info(f"Updating task {task_id} status to IN_PROGRESS")
            task = await TaskTrackingService.get_task_by_id(db, task_id)
            if task:
                # Update the database model, not the response model
                result = await db.execute(select(Task).where(Task.task_id == task_id))
                task_db = result.scalars().first()
                if task_db:
                    task_db.status = TaskStatus.IN_PROGRESS
                    await db.commit()
                    logger.info(f"Task {task_id} status updated to IN_PROGRESS")
                else:
                    logger.warning(f"Could not find task {task_id} in database")
            else:
                logger.warning(f"Task {task_id} not found")
                
            # Process the request
            logger.info(f"Processing request for task {task_id}")
            try:
                result = await orchestrator_service.process_request(request_data, db)
                logger.info(f"Request processing completed for task {task_id}")
                logger.info(f"Result: {json.dumps(result, cls=JSONEncoder)}")
            except Exception as req_error:
                logger.error(f"Error processing request for task {task_id}: {str(req_error)}")
                raise
            
            # Update task status to COMPLETED
            logger.info(f"Updating task {task_id} status to COMPLETED")
            if task:
                result = await db.execute(select(Task).where(Task.task_id == task_id))
                task_db = result.scalars().first()
                if task_db:
                    task_db.status = TaskStatus.COMPLETED
                    await db.commit()
                    logger.info(f"Task {task_id} status updated to COMPLETED")
                else:
                    logger.warning(f"Could not find task {task_id} in database for completion")
                
        logger.info(f"Completed background processing for task {task_id}")
    except Exception as e:
        logger.error(f"Error in background task {task_id}: {str(e)}")
        logger.exception(e)  # Log the full traceback
        # Update task status to FAILED if there was an error
        try:
            async with get_db() as db:
                result = await db.execute(select(Task).where(Task.task_id == task_id))
                task_db = result.scalars().first()
                if task_db:
                    task_db.status = TaskStatus.FAILED
                    task_db.error_message = str(e)
                    await db.commit()
                    logger.info(f"Task {task_id} status updated to FAILED")
                else:
                    logger.warning(f"Could not find task {task_id} in database for error update")
        except Exception as db_error:
            logger.error(f"Failed to update task status for {task_id}: {str(db_error)}")
            logger.exception(db_error)  # Log the full traceback


@router.post("/orchestrate", response_model=Dict[str, Any])
async def orchestrate(
    request: OrchestratorRequest, 
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db_dependency)
):
    """
    Endpoint that accepts orchestration requests and sends them to Event Hub.
    
    Args:
        request: The orchestration request
        background_tasks: FastAPI BackgroundTasks for asynchronous processing
        db: Database session
        
    Returns:
        A dictionary with the task ID and status
    """
    try:
        logger.info(f"Received orchestration request: {request.task_name}")
        
        # Convert Pydantic model to dict for JSON serialization
        request_data = request.model_dump()
        
        # Convert the payload items to dictionaries
        payload_dicts = [item.model_dump() for item in request.payload]
        
        # Create task tracking record in database
        task_create = TaskCreate(
            task_name=request.task_name,
            task_description=request.task_description if hasattr(request, 'task_description') else None,
            payload=payload_dicts  # Pass the list of dictionaries, not the PayloadItem objects
        )
        
        # Create the task in the database
        task = await TaskTrackingService.create_task(db, task_create)
        task_id = task.task_id
        
        # Include the task_id in the request data for correlation
        request_data["task_id"] = task_id
        
        # Send the request to the Event Hub if enabled
        if USE_EVENT_HUB:
            logger.info("Sending task to Event Hub")
            try:
                event_hub_producer = EventHubProducer()
                async with event_hub_producer as producer:
                    await producer.send_event(request_data)
                logger.info(f"Sent task to Event Hub with ID: {task_id}")
            except Exception as e:
                logger.error(f"Error sending to Event Hub: {str(e)}")
                # Fall back to direct processing if Event Hub fails
                logger.info("Falling back to direct processing")
                background_tasks.add_task(process_task_in_background, request_data, task_id)
        else:
            logger.info(f"Event Hub disabled. Processing request directly.")
            # Process the request directly
            background_tasks.add_task(process_task_in_background, request_data, task_id)
        
        return {
            "task_id": task_id,
            "status": "accepted",
            "message": "Request accepted and sent to processing queue"
        }
    
    except Exception as e:
        logger.error(f"Error processing orchestration request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )


@router.post("/orchestrate/direct", response_model=OrchestratorResponse)
async def orchestrate_direct(
    request: OrchestratorRequest,
    db: AsyncSession = Depends(get_db_dependency)
):
    """
    Endpoint that processes orchestration requests directly without using Event Hub.
    This is useful for testing or if immediate response is required.
    
    Args:
        request: The orchestration request
        db: Database session
        
    Returns:
        The orchestration response
    """
    try:
        logger.info(f"Received direct orchestration request: {request.task_name}")
        
        # Convert Pydantic model to dict
        request_data = request.model_dump()
        
        # Convert the payload items to dictionaries
        payload_dicts = [item.model_dump() for item in request.payload]
        
        # Create task tracking record in database
        task_create = TaskCreate(
            task_name=request.task_name,
            task_description=request.task_description if hasattr(request, 'task_description') else None,
            payload=payload_dicts  # Pass the list of dictionaries, not the PayloadItem objects
        )
        
        # Create the task in the database
        task = await TaskTrackingService.create_task(db, task_create)
        task_id = task.task_id
        
        # Include the task_id in the request data for correlation
        request_data["task_id"] = task_id
        
        # Process the request synchronously
        result = await orchestrator_service.process_request(request_data, db)
        
        # Update task status to completed
        await TaskTrackingService.update_task_status(db, task_id, TaskStatus.COMPLETED)
        
        # Convert to response model
        response = OrchestratorResponse(
            task_id=result["task_id"],
            status=result["status"],
            results=result["results"],
            errors=result["errors"]
        )
        
        logger.info(f"Completed direct orchestration with task ID: {response.task_id}")
        return response
    
    except Exception as e:
        logger.error(f"Error processing direct orchestration request: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error processing request: {str(e)}"
        )


@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(db: AsyncSession = Depends(get_db_dependency)):
    """
    Get all tasks.
    
    Args:
        db: Database session
        
    Returns:
        A list of tasks
    """
    try:
        tasks = await TaskTrackingService.get_all_tasks(db)
        return tasks
    except Exception as e:
        logger.error(f"Error retrieving tasks: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving tasks: {str(e)}"
        )


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str, db: AsyncSession = Depends(get_db_dependency)):
    """
    Get a task by ID.
    
    Args:
        task_id: The task ID
        db: Database session
        
    Returns:
        The task details
    """
    try:
        task = await TaskTrackingService.get_task_by_id(db, task_id)
        if not task:
            raise HTTPException(
                status_code=404,
                detail=f"Task with ID {task_id} not found"
            )
        return task
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving task {task_id}: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Error retrieving task: {str(e)}"
        ) 