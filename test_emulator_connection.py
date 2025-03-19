#!/usr/bin/env python3
"""
Test script for connecting to the Event Hub emulator directly.
Run this script from inside the orchestrator container.
"""

import os
import sys
import time
import logging
from azure.eventhub import EventHubProducerClient, EventData
from azure.eventhub.exceptions import EventHubError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Connection string for the Event Hub emulator
EVENT_HUB_CONNECTION_STR = os.environ.get(
    "EVENT_HUB_CONNECTION_STR", 
    "Endpoint=sb://emulator:5672;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=emulatorKey;UseDevelopmentEmulator=true;"
)
EVENT_HUB_NAME = os.environ.get("EVENT_HUB_NAME", "orchestrator-events")

def test_connection():
    """Test the connection to the Event Hub emulator."""
    logger.info("Testing connection to Event Hub emulator...")
    logger.info(f"Using connection string: {EVENT_HUB_CONNECTION_STR}")
    logger.info(f"Using Event Hub name: {EVENT_HUB_NAME}")
    
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            # Create a producer client
            producer = EventHubProducerClient.from_connection_string(
                conn_str=EVENT_HUB_CONNECTION_STR,
                eventhub_name=EVENT_HUB_NAME
            )
            
            logger.info("Successfully created producer client")
            
            # Create a single event
            event_data_batch = producer.create_batch()
            event_data_batch.add(EventData("Test message"))
            
            # Send the event
            producer.send_batch(event_data_batch)
            logger.info("Successfully sent event to Event Hub")
            
            # Close the producer
            producer.close()
            logger.info("Successfully closed producer client")
            
            return True
        
        except EventHubError as eh_err:
            logger.error(f"Event Hub error: {eh_err}")
        except Exception as err:
            logger.error(f"General error: {err}")
        
        retry_count += 1
        logger.info(f"Retrying ({retry_count}/{max_retries})...")
        time.sleep(2)
    
    logger.error("Failed to connect to Event Hub after multiple retries")
    return False

if __name__ == "__main__":
    success = test_connection()
    sys.exit(0 if success else 1) 