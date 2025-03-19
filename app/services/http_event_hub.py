import os
import json
import logging
import asyncio
import httpx
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger(__name__)

class HttpEventHubProducer:
    """
    HTTP-based implementation of the EventHubProducer.
    This uses the HTTP endpoint of the Event Hub emulator instead of Kafka or AMQP.
    """
    
    def __init__(self):
        """
        Initialize the HTTP producer.
        """
        self.event_hub_name = os.environ.get('EVENT_HUB_NAME', 'orchestrator-events')
        self.namespace = 'emulatorns1'  # Default namespace in the emulator
        self.base_url = os.environ.get('EVENT_HUB_HTTP_ENDPOINT', 'http://eventhubs-emulator:8080')
        
        logger.info(f"Using HTTP endpoint for Event Hub: {self.base_url}")
        logger.info(f"Using Event Hub name: {self.event_hub_name}")
        logger.info(f"Using namespace: {self.namespace}")
    
    async def send_event(self, event_data: Dict[str, Any]) -> None:
        """
        Send an event to the Event Hub using HTTP POST.
        
        Args:
            event_data (Dict[str, Any]): Event data to send
        """
        try:
            # Convert the event data to JSON
            event_json = json.dumps(event_data)
            
            # Construct the URL for sending events
            url = f"{self.base_url}/api/namespaces/{self.namespace}/eventhubs/{self.event_hub_name}/messages"
            
            logger.info(f"Sending event to HTTP endpoint: {url}")
            
            # Send the event using httpx
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    url,
                    content=event_json,
                    headers={"Content-Type": "application/json"}
                )
                
                # Check if the request was successful
                response.raise_for_status()
                
                logger.info(f"Event sent successfully via HTTP. Status: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Failed to send event via HTTP: {str(e)}")
            raise

class HttpEventHubConsumer:
    """
    HTTP-based implementation of the EventHubConsumer.
    This polls the HTTP endpoint of the Event Hub emulator instead of using Kafka or AMQP.
    """
    
    def __init__(self, consumer_group: str = '$default'):
        """
        Initialize the HTTP consumer.
        
        Args:
            consumer_group (str): Consumer group name
        """
        self.event_hub_name = os.environ.get('EVENT_HUB_NAME', 'orchestrator-events')
        self.namespace = 'emulatorns1'  # Default namespace in the emulator
        self.base_url = os.environ.get('EVENT_HUB_HTTP_ENDPOINT', 'http://eventhubs-emulator:8080')
        self.consumer_group = consumer_group
        self.polling_interval = 1.0  # seconds
        
        logger.info(f"Using HTTP endpoint for Event Hub consumption: {self.base_url}")
        logger.info(f"Using Event Hub name: {self.event_hub_name}")
        logger.info(f"Using namespace: {self.namespace}")
        logger.info(f"Using consumer group: {self.consumer_group}")
    
    async def start_receiving(self, callback: Callable):
        """
        Start receiving events from the Event Hub using HTTP polling.
        
        Args:
            callback: Callback function to process events
        """
        logger.info(f"Starting to receive events from HTTP endpoint")
        
        # Construct the URL for receiving events
        url = f"{self.base_url}/api/namespaces/{self.namespace}/eventhubs/{self.event_hub_name}/consumergroups/{self.consumer_group}/messages"
        
        logger.info(f"Polling URL: {url}")
        
        while True:
            try:
                # Fetch events using HTTP GET
                async with httpx.AsyncClient() as client:
                    response = await client.get(
                        url,
                        headers={"Accept": "application/json"},
                        timeout=10.0
                    )
                    
                    # Check if the request was successful
                    response.raise_for_status()
                    
                    # Parse the response
                    events = response.json()
                    
                    # Process each event
                    for event in events:
                        try:
                            # Create a task to process the event
                            asyncio.create_task(callback(event))
                        except Exception as e:
                            logger.error(f"Error processing event: {str(e)}")
                
                # Wait before polling again
                await asyncio.sleep(self.polling_interval)
                
            except httpx.HTTPStatusError as e:
                if e.response.status_code == 404:
                    # No events available, just wait and try again
                    logger.debug("No events available")
                else:
                    logger.error(f"HTTP error while fetching events: {str(e)}")
                
                await asyncio.sleep(self.polling_interval)
                
            except Exception as e:
                logger.error(f"Error fetching events: {str(e)}")
                await asyncio.sleep(self.polling_interval * 2)  # Wait longer on error 