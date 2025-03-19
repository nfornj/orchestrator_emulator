import asyncio
import json
import logging
import os
import socket
from typing import List, Callable, Dict, Any
import uuid
from datetime import datetime

from azure.eventhub import EventData
from azure.eventhub.aio import EventHubProducerClient, EventHubConsumerClient
from azure.eventhub.extensions.checkpointstoreblobaio import BlobCheckpointStore

# Import our UUID encoder
from app.event_hub import UUIDEncoder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Determine if we're running in Docker or locally
def is_running_in_docker():
    """Check if the application is running inside a Docker container."""
    try:
        with open('/proc/self/cgroup', 'r') as f:
            return any('docker' in line for line in f)
    except:
        return False

# Choose the appropriate connection string based on environment
def get_default_connection_string():
    """Get the appropriate connection string based on the environment."""
    if is_running_in_docker():
        # For containers on the same network, use the service name and port
        return "Endpoint=sb://emulator:5672;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=emulatorKey;UseDevelopmentEmulator=true;"
    else:
        # For local development, use localhost with port
        return "Endpoint=sb://localhost:5672;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=emulatorKey;UseDevelopmentEmulator=true;"

# Configuration - can be overridden with environment variables
EVENT_HUB_CONNECTION_STR = os.getenv("EVENT_HUB_CONNECTION_STR", get_default_connection_string())
EVENT_HUB_NAME = os.getenv("EVENT_HUB_NAME", "orchestrator-events")
EVENT_HUB_CONSUMER_GROUP = os.getenv("EVENT_HUB_CONSUMER_GROUP", "$Default")

# Storage connection string similarly depends on environment
def get_default_storage_connection_string():
    """Get the appropriate storage connection string based on the environment."""
    if is_running_in_docker():
        # For containers on the same network, use the container name
        return "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://azurite:10000/devstoreaccount1;"
    else:
        # For local development, use localhost
        return "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"

STORAGE_CONNECTION_STRING = os.getenv("STORAGE_CONNECTION_STRING", get_default_storage_connection_string())
STORAGE_CONTAINER_NAME = os.getenv("STORAGE_CONTAINER_NAME", "eventhub-checkpoints")

# Log the connection settings (mask sensitive info)
def mask_connection_string(conn_str):
    """Mask sensitive information in connection strings for logging."""
    if not conn_str:
        return "None"
    masked = conn_str
    if "SharedAccessKey=" in masked:
        # Mask the shared access key
        parts = masked.split("SharedAccessKey=")
        if len(parts) > 1:
            key_and_rest = parts[1].split(";", 1)
            if len(key_and_rest) > 1:
                masked = f"{parts[0]}SharedAccessKey=***MASKED***;{key_and_rest[1]}"
            else:
                masked = f"{parts[0]}SharedAccessKey=***MASKED***"
    return masked

logger.info(f"Using Event Hub connection string: {mask_connection_string(EVENT_HUB_CONNECTION_STR)}")
logger.info(f"Using Event Hub name: {EVENT_HUB_NAME}")
logger.info(f"Using Storage connection string: {mask_connection_string(STORAGE_CONNECTION_STRING)}")


class EventHubProducer:
    """
    Azure Event Hub Producer client for sending orchestration requests.
    """
    
    def __init__(self):
        """
        Initialize the Event Hub Producer client.
        """
        eventhub_config = get_eventhub_config()
        self.connection_string = eventhub_config["connection_string"]
        self.event_hub_name = eventhub_config["event_hub_name"]
        self.producer_client = None
        
    async def __aenter__(self):
        """
        Create the producer client when entering the context manager.
        """
        logger.info(f"Creating producer client for Event Hub: {self.event_hub_name}")
        self.producer_client = EventHubProducerClient.from_connection_string(
            conn_str=self.connection_string,
            eventhub_name=self.event_hub_name
        )
        await self.producer_client.__aenter__()
        logger.info("Producer client created successfully")
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """
        Close the producer client when exiting the context manager.
        """
        if self.producer_client:
            await self.producer_client.__aexit__(exc_type, exc_val, exc_tb)
            logger.info("Producer client closed")
    
    async def send_event(self, event_data: Dict[str, Any]) -> str:
        """
        Send an event to the Event Hub.
        
        Args:
            event_data: The event data to send
            
        Returns:
            The task ID generated for this event
        """
        try:
            # Generate a task ID for this event if one is not provided
            task_id = event_data.get("task_id", str(uuid.uuid4()))
            
            # Add task_id to event data if not present
            if "task_id" not in event_data:
                event_data["task_id"] = task_id
                
            # Convert the event data to a JSON string with UUID and other custom types properly encoded
            event_json = json.dumps(event_data, cls=UUIDEncoder)
            
            # Create an EventData object with the JSON payload
            event_data_obj = EventData(event_json)
            
            # Add properties to the event
            event_data_obj.properties = {
                "task_id": task_id,
                "timestamp": datetime.utcnow().isoformat()
            }
            
            # Send the event
            event_batch = await self.producer_client.create_batch()
            event_batch.add(event_data_obj)
            await self.producer_client.send_batch(event_batch)
            
            logger.info(f"Event sent to Event Hub with task_id: {task_id}")
            
            return task_id
        except Exception as e:
            logger.error(f"Error sending event: {str(e)}")
            raise


class EventHubConsumer:
    """
    A class for consuming events from Azure Event Hub.
    """
    
    def __init__(
        self,
        connection_str: str = EVENT_HUB_CONNECTION_STR,
        eventhub_name: str = EVENT_HUB_NAME,
        consumer_group: str = EVENT_HUB_CONSUMER_GROUP,
        storage_conn_str: str = STORAGE_CONNECTION_STRING,
        container_name: str = STORAGE_CONTAINER_NAME
    ):
        """
        Initialize the EventHubConsumer.
        
        Args:
            connection_str: The Event Hub connection string
            eventhub_name: The Event Hub instance name
            consumer_group: The consumer group to use
            storage_conn_str: Connection string for the Azure Storage account (for checkpointing)
            container_name: Storage container name for checkpoints
        """
        self.connection_str = connection_str
        self.eventhub_name = eventhub_name
        self.consumer_group = consumer_group
        self.storage_conn_str = storage_conn_str
        self.container_name = container_name
    
    async def start_receiving(self, process_event_batch_callback: Callable):
        """
        Start receiving events from the Event Hub.
        
        Args:
            process_event_batch_callback: Callback function to process batches of events
        """
        # Create a checkpoint store for persisting checkpoints
        checkpoint_store = BlobCheckpointStore.from_connection_string(
            self.storage_conn_str,
            self.container_name
        )
        
        # Create a consumer client
        consumer_client = EventHubConsumerClient.from_connection_string(
            self.connection_str,
            consumer_group=self.consumer_group,
            eventhub_name=self.eventhub_name,
            checkpoint_store=checkpoint_store
        )
        
        logger.info("Starting to receive events from Event Hub...")
        
        async def on_event_batch(partition_context, events):
            # Process the batch of events
            if events:
                logger.info(f"Received {len(events)} events from partition {partition_context.partition_id}")
                try:
                    await process_event_batch_callback(events)
                    await partition_context.update_checkpoint()
                except Exception as e:
                    logger.error(f"Error processing event batch: {str(e)}")
        
        try:
            async with consumer_client:
                await consumer_client.receive_batch(
                    on_event_batch=on_event_batch,
                    starting_position="-1"  # "-1" is from the end of the partition
                )
        except Exception as e:
            logger.error(f"Error in consumer client: {str(e)}")
        finally:
            logger.info("Stopped receiving events from Event Hub")


async def process_events_example(events: List[EventData]):
    """
    Example function to process a batch of events.
    This is just a placeholder - in a real application, you would replace this
    with your actual event processing logic.
    
    Args:
        events: A list of EventData objects
    """
    for event in events:
        # Extract the event body
        event_body = json.loads(event.body_as_str())
        task_id = event.properties.get("task_id", "unknown")
        
        logger.info(f"Processing event - Task ID: {task_id}")
        # Process the event (in a real application, this would call your business logic)
        
        # For example, you might call an external API, save to database, etc.
        await asyncio.sleep(0.1)  # Simulate some async work
        
    logger.info(f"Processed {len(events)} events") 

def get_eventhub_config() -> Dict[str, str]:
    """
    Get the Event Hub configuration from environment variables.
    
    Returns:
        Dictionary with connection_string, event_hub_name, consumer_group, and storage_connection_string
    """
    # Get Event Hub connection string from environment variable
    connection_string = os.environ.get("EVENT_HUB_CONNECTION_STRING", "Endpoint=sb://localhost:5672;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=123456;UseDevelopmentEmulator=true;")
    
    # Mask the access key in logs for security
    if connection_string and "SharedAccessKey=" in connection_string:
        masked_connection_string = connection_string.split("SharedAccessKey=")[0] + "SharedAccessKey=***MASKED***" + connection_string.split("SharedAccessKey=")[1].split(";", 1)[1]
        logger.info(f"Using Event Hub connection string: {masked_connection_string}")
    else:
        logger.info(f"Using Event Hub connection string: {connection_string}")
    
    # Get Event Hub name from environment variable
    event_hub_name = os.environ.get("EVENT_HUB_NAME", "orchestrator-events")
    logger.info(f"Using Event Hub name: {event_hub_name}")
    
    # Get Consumer Group from environment variable (default to $Default)
    consumer_group = os.environ.get("EVENT_HUB_CONSUMER_GROUP", "$Default")
    
    # Get Storage connection string for checkpointing from environment variable
    storage_connection_string = os.environ.get(
        "STORAGE_CONNECTION_STRING", 
        "DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;"
    )
    logger.info(f"Using Storage connection string: {storage_connection_string}")
    
    return {
        "connection_string": connection_string,
        "event_hub_name": event_hub_name,
        "consumer_group": consumer_group,
        "storage_connection_string": storage_connection_string
    } 