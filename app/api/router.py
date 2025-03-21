import uuid
from fastapi import APIRouter, HTTPException, BackgroundTasks
from app.api.models import TaskPayload, TaskResponse, TaskStatus
from app.services.storage import store_payload_in_redis, get_task_status
from app.services.eventhub import send_to_eventhub
from azure.eventhub.aio import EventHubProducerClient
from app.core.config import settings

router = APIRouter()

@router.post("/tasks", response_model=TaskResponse)
async def create_task(task: TaskPayload):
    # Generate a unique task_id
    task_id = str(uuid.uuid4())
    
    # Store the payload in Redis
    await store_payload_in_redis(task_id, task)
    
    # Send metadata to Event Hub for each compute item
    for compute in task.compute:
        await send_to_eventhub(task_id, compute.scenario_id, compute.business_type_id)
    
    # Return the task_id to the user
    return TaskResponse(task_id=task_id)

@router.get("/tasks/{task_id}", response_model=TaskStatus)
async def get_task(task_id: str):
    # Get task status
    status_data = await get_task_status(task_id)
    if not status_data:
        raise HTTPException(status_code=404, detail="Task not found")
    
    return TaskStatus(**status_data)

@router.get("/health")
async def health_check():
    """Health check endpoint that also tests Event Hub connection."""
    result = {
        "status": "ok",
        "services": {
            "api": "ok"
        }
    }
    
    # Check Event Hub connection
    try:
        connection_string = settings.EVENTHUB_CONNECTION_STRING
        topic_name = settings.EVENTHUB_NAME
        
        producer = EventHubProducerClient.from_connection_string(
            conn_str=connection_string,
            eventhub_name=topic_name
        )
        
        async with producer:
            result["services"]["eventhub"] = "ok"
    except Exception as e:
        result["services"]["eventhub"] = f"error: {str(e)}"
        result["status"] = "degraded"
    
    return result 