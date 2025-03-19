import asyncio
import logging
import os
import json
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, BackgroundTasks, Depends, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware

from app.api.endpoints import router as api_router
from app.orchestrators.router import router as orchestrator_router
from app.services.event_hub import EventHubConsumer, EventData
# Import the Kafka implementation
from app.services.kafka_event_hub import KafkaEventHubConsumer
# Import the HTTP implementation
from app.services.http_event_hub import HttpEventHubConsumer
from app.services.orchestrator import OrchestratorService
# Import database components
from app.database import get_db_dependency, AsyncSession, get_db
from app.models.task_tracking import Task, ServiceRequest, Base
from app.services.task_tracking import TaskTrackingService
from app.schemas.task_tracking import TaskCreate
from app.models.task_tracking import TaskStatus
from app.utils import JSONEncoder
from app.middleware import JSONEncoderMiddleware
from alembic.config import Config
from alembic import command

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Initialize services
orchestrator_service = OrchestratorService()

# Global variable to store the event hub consumer task
event_hub_task = None

# Determine which client implementation to use
USE_KAFKA = os.environ.get("USE_KAFKA", "False").lower() == "true"
USE_HTTP = os.environ.get("USE_HTTP", "False").lower() == "true"

async def get_async_db():
    """Get a database session outside of the request context"""
    async with get_db() as session:
        yield session

async def process_kafka_events(event_data):
    """
    Process events from the Kafka topic.
    
    Args:
        event_data: The event data to process
    """
    try:
        # The event data is already a dictionary from the Kafka consumer
        task_id = event_data.get("task_id", "unknown")
        
        logger.info(f"Processing event from Kafka - Task ID: {task_id}")
        
        # Get a DB session
        async with get_db() as db:
            # Process the request with database session
            await orchestrator_service.process_request(event_data, db)
        
    except Exception as e:
        logger.error(f"Error processing Kafka event: {str(e)}")

async def process_http_events(event_data):
    """
    Process events from the HTTP endpoint.
    
    Args:
        event_data: The event data to process
    """
    try:
        # The event data is already a dictionary from the HTTP consumer
        task_id = event_data.get("task_id", "unknown")
        
        logger.info(f"Processing event from HTTP - Task ID: {task_id}")
        
        # Get a DB session
        async with get_db() as db:
            # Process the request with database session
            await orchestrator_service.process_request(event_data, db)
        
    except Exception as e:
        logger.error(f"Error processing HTTP event: {str(e)}")

async def process_amqp_events(events):
    """
    Process events from the Event Hub AMQP protocol.
    
    Args:
        events: The events to process
    """
    for event in events:
        try:
            # Parse the event body
            event_body = json.loads(event.body_as_str())
            task_id = event.properties.get("task_id", "unknown")
            
            logger.info(f"Processing event from Event Hub AMQP - Task ID: {task_id}")
            
            # Get a DB session
            async with get_db() as db:
                # Check if the task exists, if not, create it
                if task_id == "unknown":
                    # Generate a task_id and create a new task
                    task_create = TaskCreate(
                        task_name=event_body.get("task_name", "Unknown Task"),
                        task_description=event_body.get("task_description", "Task from Event Hub"),
                        payload=event_body.get("payload", [])
                    )
                    task = await TaskTrackingService.create_task(db, task_create)
                    event_body["task_id"] = task.task_id
                    task_id = task.task_id
                else:
                    # Check if task exists
                    task = await TaskTrackingService.get_task_by_id(db, task_id)
                    if not task:
                        # Create a new task with the existing task_id
                        task_create = TaskCreate(
                            task_name=event_body.get("task_name", "Unknown Task"),
                            task_description=event_body.get("task_description", "Task from Event Hub"),
                            payload=event_body.get("payload", [])
                        )
                        task = await TaskTrackingService.create_task(db, task_create)
                        # Update the task_id to ensure it matches
                        task.task_id = task_id
                        await db.commit()
                
                # Process the request with database session
                await orchestrator_service.process_request(event_body, db)
            
        except Exception as e:
            logger.error(f"Error processing AMQP event: {str(e)}")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Lifespan context manager for FastAPI.
    This is used for startup and shutdown events.
    """
    # Run database migrations on startup
    try:
        logger.info("Running database migrations...")
        alembic_cfg = Config("alembic.ini")
        command.upgrade(alembic_cfg, "head")
    except Exception as e:
        logger.error(f"Error running database migrations: {str(e)}")
        logger.warning("Continuing without database migrations...")
    
    # Start event consumer
    global event_hub_task
    
    if USE_KAFKA:
        # Use Kafka implementation
        logger.info("Starting Kafka consumer...")
        try:
            kafka_consumer = KafkaEventHubConsumer()
            event_hub_task = asyncio.create_task(kafka_consumer.receive_events(process_kafka_events))
            logger.info("Kafka consumer started successfully.")
        except Exception as e:
            logger.error(f"Failed to start Kafka consumer: {str(e)}")
    elif USE_HTTP:
        # Use HTTP implementation
        logger.info("Starting HTTP consumer...")
        try:
            http_consumer = HttpEventHubConsumer()
            event_hub_task = asyncio.create_task(http_consumer.receive_events(process_http_events))
            logger.info("HTTP consumer started successfully.")
        except Exception as e:
            logger.error(f"Failed to start HTTP consumer: {str(e)}")
    else:
        # Use Event Hub AMQP implementation
        logger.info("Starting Event Hub AMQP consumer...")
        try:
            event_hub_consumer = EventHubConsumer()
            event_hub_task = asyncio.create_task(event_hub_consumer.receive_events(process_amqp_events))
            logger.info("Event Hub AMQP consumer started successfully.")
        except Exception as e:
            logger.error(f"Failed to start Event Hub AMQP consumer: {str(e)}")
    
    # Yield control back to FastAPI
    yield
    
    # Cleanup on shutdown
    if event_hub_task and not event_hub_task.done():
        logger.info("Cancelling event consumer task...")
        event_hub_task.cancel()
        try:
            await event_hub_task
        except asyncio.CancelledError:
            logger.info("Event consumer task cancelled.")


# Create FastAPI app with middleware
app = FastAPI(
    title="Orchestrator Service",
    description="Service to orchestrate processing across various sub-services",
    version="0.1.0",
    lifespan=lifespan,
    default_response_class=JSONResponse,  # Set the default response class
    json_encoder=JSONEncoder  # Use our custom JSON encoder for all responses
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom JSON encoder middleware
app.add_middleware(JSONEncoderMiddleware)

# Include API routers
app.include_router(api_router, prefix="/api")
app.include_router(orchestrator_router, prefix="/orchestrator")


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    protocol = "http" if USE_HTTP else ("kafka" if USE_KAFKA else "amqp")
    return {
        "status": "healthy", 
        "event_hub_mode": protocol
    }


if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8000))
    
    # Run the application with uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=port,
        reload=bool(os.getenv("DEBUG", "False").lower() == "true"),
    ) 