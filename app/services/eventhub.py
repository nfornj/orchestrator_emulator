import json
import asyncio
import logging
import sys
import traceback
import socket
import os
from datetime import datetime, timezone
from azure.eventhub import EventData
from azure.eventhub.aio import EventHubProducerClient
from app.core.config import settings
from app.services.processor import process_task
from confluent_kafka import Producer, Consumer, KafkaError

# Debug: Print file path at import time
print(f"LOADED EVENTHUB.PY FROM: {os.path.abspath(__file__)}")
print(f"USING CONFLUENT KAFKA VERSION: {Producer.__module__}")

# Dictionary to track currently processing tasks with scenario_id and business_type_id as key
processing_tasks = {}

async def check_host_connectivity(host, port):
    """Utility function to check if a host:port is reachable"""
    try:
        # Create a socket object
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        # Set a timeout
        s.settimeout(2)
        # Try to connect
        result = s.connect_ex((host, port))
        s.close()
        
        if result == 0:
            logging.info(f"Connection to {host}:{port} succeeded")
            return True
        else:
            logging.error(f"Connection to {host}:{port} failed with error code {result}")
            return False
    except Exception as e:
        logging.error(f"Error checking connectivity to {host}:{port}: {str(e)}")
        return False

async def send_message_via_kafka(task_id: str, scenario_id: str, business_type_id: str):
    """Send a message via Kafka using confluent_kafka library."""
    logging.info(f"Sending via Kafka for task {task_id}")
    
    try:
        # Create a Kafka producer with the specific bootstrap servers and SASL configuration
        bootstrap_servers = "eventhubs-emulator:9092"
        logging.info(f"Connecting to Kafka brokers: {bootstrap_servers}")
        
        # Configure Kafka with SASL PLAIN for Azure Event Hubs Emulator
        connection_string = "Endpoint=sb://eventhubs-emulator;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;UseDevelopmentEmulator=true;"
        kafka_config = {
            'bootstrap.servers': bootstrap_servers,
            'security.protocol': 'SASL_PLAINTEXT',
            'sasl.mechanism': 'PLAIN',
            'sasl.username': '$ConnectionString',
            'sasl.password': connection_string,
            'client.id': socket.gethostname()
        }
        
        # Create the confluent_kafka Producer
        producer = Producer(kafka_config)
        
        # Create message
        message = {
            "task_id": task_id,
            "scenario_id": scenario_id,
            "business_type_id": business_type_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Serialize the message
        value = json.dumps(message)
        topic_name = "orchestrator"  # Use the eventhub name which is 'orchestrator'
        
        # Create a partition key by combining scenario_id and business_type_id
        # This ensures that all messages for the same scenario+business type go to the same partition
        partition_key = f"{scenario_id}:{business_type_id}"
        
        logging.info(f"Sending message to Kafka topic {topic_name} with partition key {partition_key}: {message}")
        
        # Send the message with the partition key
        producer.produce(topic_name, key=partition_key, value=value)
        
        # Wait for any outstanding messages to be delivered and delivery reports received
        producer.flush(timeout=10)
        
        logging.info(f"Successfully sent message to Kafka with partition key {partition_key}: {message}")
        return True
            
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        tb = sys.exc_info()[2]
        logging.error(f"Error sending message to Kafka: {error_type}: {error_message}")
        
        # Log detailed traceback information
        for line in traceback.format_tb(tb):
            logging.error(f"Kafka Traceback: {line.strip()}")
        
        return False

async def send_to_eventhub(task_id: str, scenario_id: str, business_type_id: str):
    """Send a message to Azure Event Hub using Confluent Kafka."""
    return await send_message_via_kafka(task_id, scenario_id, business_type_id)

async def init_eventhub_consumer():
    """Initialize and run the EventHub consumer using Confluent Kafka."""
    try:
        logging.info("Initializing Confluent Kafka consumer")
        kafka_success = await init_kafka_consumer()
        
        if not kafka_success:
            logging.error("Failed to initialize Confluent Kafka consumer")
            return False
        
        return True
    except Exception as e:
        logging.error(f"Error in EventHub consumer initialization: {str(e)}")
        return False

async def init_kafka_consumer():
    """Initialize and run the Kafka consumer using confluent_kafka library."""
    print("DEBUG: Using confluent_kafka for consumer initialization")
    max_retries = 5
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            topic_name = "orchestrator"  # Use the eventhub name 'orchestrator'
            logging.info(f"Initializing Confluent Kafka consumer for topic {topic_name} (attempt {retry_count + 1}/{max_retries})")
            
            # Use a consistent consumer group
            group_id = "orchestrator-consumer-group"
            
            # Kafka connection settings with SASL PLAIN for Azure Event Hubs Emulator
            connection_string = "Endpoint=sb://eventhubs-emulator;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;UseDevelopmentEmulator=true;"
            kafka_config = {
                'bootstrap.servers': 'eventhubs-emulator:9092',
                'security.protocol': 'SASL_PLAINTEXT',
                'sasl.mechanism': 'PLAIN',
                'sasl.username': '$ConnectionString',
                'sasl.password': connection_string,
                'group.id': group_id,
                'auto.offset.reset': 'earliest',
                'enable.auto.commit': False,  # We'll commit manually after processing
                'client.id': socket.gethostname(),
                'partition.assignment.strategy': 'cooperative-sticky',  # Sticky assignment for better handling of partitions
                'max.poll.interval.ms': 300000,  # 5 minutes to process messages before rebalance
                'session.timeout.ms': 45000,  # 45 seconds timeout
                'heartbeat.interval.ms': 15000  # 15 seconds heartbeat
            }
            
            # Check connectivity before proceeding
            if not await check_host_connectivity('eventhubs-emulator', 9092):
                logging.error("Cannot connect to Kafka broker at eventhubs-emulator:9092")
                raise ConnectionError("Failed to connect to Kafka broker")
            
            # Create the consumer
            consumer = Consumer(kafka_config)
            
            # Subscribe to the topic
            consumer.subscribe([topic_name])
            logging.info(f"Successfully subscribed to topic {topic_name}")
            
            # Start a loop in a background task to consume messages
            logging.info("Starting background task for Kafka message consumption")
            asyncio.create_task(kafka_consumer_loop(consumer, topic_name))
            
            # Return success since we've started the background task
            return True
            
        except (ConnectionError, Exception) as e:
            retry_count += 1
            logging.error(f"Error initializing Kafka consumer (attempt {retry_count}/{max_retries}): {str(e)}")
            
            # If we created a consumer, close it properly
            try:
                if 'consumer' in locals():
                    consumer.close()
                    logging.info("Kafka consumer closed due to error")
            except Exception as close_error:
                logging.error(f"Error closing Kafka consumer: {str(close_error)}")
            
            if retry_count < max_retries:
                wait_time = 2 ** retry_count  # Exponential backoff
                logging.info(f"Retrying in {wait_time} seconds...")
                await asyncio.sleep(wait_time)
            else:
                logging.error(f"Failed to initialize Kafka consumer after {max_retries} attempts")
                return False
    
    return False  # This should never be reached, but added for clarity

async def kafka_consumer_loop(consumer, topic_name):
    """Run a loop to consume Kafka messages in the background."""
    try:
        logging.info(f"Starting Kafka consumer loop for topic {topic_name}")
        
        # Dictionary to track the latest task_id for each scenario_id+business_type_id combination
        # Using a dictionary of {partition_key: {'task_id': '...', 'timestamp': '...'}}
        latest_tasks = {}
        
        # Keep running to consume messages
        while True:
            try:
                # Poll for messages with a timeout
                msg = consumer.poll(timeout=1.0)
                
                if msg is None:
                    # No message received, continue polling
                    await asyncio.sleep(0.1)  # Short sleep to avoid CPU spinning
                    continue
                
                if msg.error():
                    # Handle errors
                    if msg.error().code() == KafkaError._PARTITION_EOF:
                        # End of partition, not an error
                        logging.info(f"Reached end of partition for {msg.topic()}/{msg.partition()}")
                    else:
                        # Log actual error
                        logging.error(f"Kafka consumer error: {msg.error()}")
                    continue
                
                # Process the message
                try:
                    # Get the message value
                    message_bytes = msg.value()
                    
                    # Decode and parse the message
                    try:
                        message_str = message_bytes.decode('utf-8')
                        message_data = json.loads(message_str)
                        logging.info(f"Received message from Kafka: {message_data}")
                    except (json.JSONDecodeError, UnicodeDecodeError) as decode_error:
                        logging.error(f"Error decoding Kafka message: {str(decode_error)}")
                        # Still commit the message to avoid reprocessing corrupted data
                        consumer.commit(msg)
                        continue
                    
                    # Extract the necessary data for processing
                    task_id = message_data.get("task_id")
                    scenario_id = message_data.get("scenario_id")
                    business_type_id = message_data.get("business_type_id")
                    timestamp = message_data.get("timestamp", "")
                    
                    if not all([task_id, scenario_id, business_type_id]):
                        logging.error(f"Missing required fields in message: {message_data}")
                        # Commit the message since we can't process it anyway
                        consumer.commit(msg)
                        continue
                    
                    # Create a unique key for this task (same as the partition key in the producer)
                    partition_key = f"{scenario_id}:{business_type_id}"
                    
                    # Check if we've seen this partition_key before and if this is a newer message
                    if partition_key in latest_tasks:
                        if timestamp <= latest_tasks[partition_key]['timestamp']:
                            logging.info(f"Skipping older or same-time message for {partition_key}. "
                                        f"Current timestamp: {timestamp}, Latest timestamp: {latest_tasks[partition_key]['timestamp']}")
                            consumer.commit(msg)
                            continue
                        
                        # If there's an older task being processed, we should skip this one for now
                        # We'll come back to it when the older task finishes
                        if partition_key in processing_tasks and processing_tasks[partition_key] != task_id:
                            logging.info(f"A task with key {partition_key} is already being processed. "
                                        f"This newer task {task_id} will be processed later.")
                            # Don't commit this message so it can be reprocessed later
                            continue
                    
                    # Update the latest task for this key
                    latest_tasks[partition_key] = {
                        'task_id': task_id,
                        'timestamp': timestamp
                    }
                    
                    # If this scenario/business_type is already being processed, skip it for now
                    if partition_key in processing_tasks and processing_tasks[partition_key] != task_id:
                        logging.info(f"Task {task_id} with key {partition_key} is already being processed. Skipping.")
                        # Don't commit this message so it can be reprocessed later
                        continue
                    
                    # Mark this task as being processed
                    processing_tasks[partition_key] = task_id
                    
                    try:
                        # Process the task
                        logging.info(f"Processing task from Kafka: {task_id} for {partition_key}")
                        await process_task(task_id, scenario_id, business_type_id)
                        logging.info(f"Successfully processed task from Kafka: {task_id} for {partition_key}")
                    finally:
                        # Remove from processing tasks
                        if processing_tasks.get(partition_key) == task_id:
                            del processing_tasks[partition_key]
                    
                    # Commit the offset to acknowledge processing
                    consumer.commit(msg)
                    logging.debug(f"Committed offset for task: {task_id}")
                    
                except Exception as process_error:
                    logging.error(f"Error processing Kafka message: {str(process_error)}")
                    # Log detailed traceback for better diagnostics
                    tb = sys.exc_info()[2]
                    for line in traceback.format_tb(tb):
                        logging.error(f"Process message error: {line.strip()}")
            
            except Exception as loop_error:
                logging.error(f"Error in Kafka consumer loop: {str(loop_error)}")
                # Short sleep before trying again
                await asyncio.sleep(1)
                
    except Exception as e:
        logging.error(f"Fatal error in Kafka consumer loop: {str(e)}")
    finally:
        # Always close the consumer properly when done
        try:
            consumer.close()
            logging.info("Kafka consumer closed cleanly")
        except Exception as close_error:
            logging.error(f"Error closing Kafka consumer: {str(close_error)}") 