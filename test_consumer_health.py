#!/usr/bin/env python3
"""
Test script to check consumer health in the TrueCost Orchestrator.
This script will:
1. Check Kafka connectivity
2. Send a test message
3. Directly check if the message was added to Kafka
4. Monitor to see if the message is processed
"""
import asyncio
import json
import logging
import socket
import sys
import time
import uuid
import requests
from datetime import datetime, timezone
from confluent_kafka import Producer, Consumer, KafkaError

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
API_URL = "http://localhost:8080/tasks"
KAFKA_CONFIG = {
    'bootstrap.servers': 'localhost:9092',  # Use localhost for direct client access
    'security.protocol': 'SASL_PLAINTEXT',
    'sasl.mechanism': 'PLAIN',
    'sasl.username': '$ConnectionString',
    'sasl.password': 'Endpoint=sb://eventhubs-emulator:9092;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;UseDevelopmentEmulator=true;Transport=Kafka;',
}
TOPIC_NAME = "orchestrator"
MAX_CHECKS = 20
CHECK_INTERVAL = 3  # Seconds between checks

def check_kafka_connectivity():
    """Check if Kafka broker is accessible."""
    try:
        logging.info("Checking Kafka connectivity...")
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
        result = s.connect_ex(('localhost', 9092))
        s.close()
        
        if result == 0:
            logging.info("Kafka is accessible at localhost:9092")
            return True
        else:
            logging.error(f"Cannot connect to Kafka broker at localhost:9092 - error code {result}")
            return False
    except Exception as e:
        logging.error(f"Error checking Kafka connectivity: {str(e)}")
        return False

def send_message_directly():
    """Send a message directly to Kafka."""
    logging.info("Attempting to send a message directly to Kafka...")
    
    # Generate unique IDs for testing
    test_id = uuid.uuid4().hex[:8]
    task_id = str(uuid.uuid4())
    scenario_id = f"test-scenario-{test_id}"
    business_type_id = f"test-business-{test_id}"
    
    # Create a producer
    try:
        producer = Producer(KAFKA_CONFIG)
        
        # Create message
        message = {
            "task_id": task_id,
            "scenario_id": scenario_id,
            "business_type_id": business_type_id,
            "timestamp": datetime.now(timezone.utc).isoformat()
        }
        
        # Serialize the message
        value = json.dumps(message)
        
        # Create a partition key by combining scenario_id and business_type_id
        partition_key = f"{scenario_id}:{business_type_id}"
        
        logging.info(f"Sending message to Kafka topic {TOPIC_NAME} with partition key {partition_key}: {message}")
        
        # Send the message with the partition key
        producer.produce(TOPIC_NAME, key=partition_key, value=value)
        
        # Wait for any outstanding messages to be delivered
        producer.flush(timeout=10)
        
        logging.info(f"Successfully sent message to Kafka with partition key {partition_key}")
        
        return {
            "task_id": task_id,
            "scenario_id": scenario_id,
            "business_type_id": business_type_id,
            "partition_key": partition_key
        }
    except Exception as e:
        logging.error(f"Error sending message directly to Kafka: {str(e)}")
        return None

def check_message_in_kafka(message_info):
    """Check if the message appears in the Kafka topic."""
    logging.info("Checking if message appears in Kafka topic...")
    
    # Configure consumer
    consumer_config = KAFKA_CONFIG.copy()
    consumer_config.update({
        'group.id': f'test-consumer-{uuid.uuid4().hex[:8]}',  # Unique group to start from beginning
        'auto.offset.reset': 'earliest',  # Start reading from the beginning
    })
    
    consumer = Consumer(consumer_config)
    consumer.subscribe([TOPIC_NAME])
    
    try:
        found_message = False
        start_time = time.time()
        
        while time.time() - start_time < 20:  # Try for 20 seconds
            msg = consumer.poll(1.0)
            
            if msg is None:
                continue
                
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logging.info(f"Reached end of partition: {msg.topic()} [{msg.partition()}]")
                else:
                    logging.error(f"Error consuming message: {msg.error()}")
                continue
            
            try:
                msg_key = msg.key().decode('utf-8') if msg.key() else None
                msg_value = json.loads(msg.value().decode('utf-8'))
                
                logging.info(f"Checking message: key={msg_key}, task_id={msg_value.get('task_id')}")
                
                # Check if this is our message
                if msg_value.get('task_id') == message_info['task_id']:
                    logging.info(f"Found our message in Kafka! Partition: {msg.partition()}")
                    found_message = True
                    
                    # Store the partition information
                    message_info['partition'] = msg.partition()
                    break
            except Exception as e:
                logging.error(f"Error parsing message: {e}")
        
        if found_message:
            logging.info("Message was successfully written to Kafka")
        else:
            logging.warning("Could not find our message in Kafka within the timeout period")
        
        return found_message
    finally:
        consumer.close()
        logging.info("Kafka consumer closed")

def create_task_via_api():
    """Create a task through the API."""
    logging.info("Creating a task through the API...")
    
    # Generate unique IDs for testing
    test_id = uuid.uuid4().hex[:8]
    scenario_id = f"api-scenario-{test_id}"
    business_type_id = f"api-business-{test_id}"
    
    payload = {
        "task_name": f"Consumer Health Test {test_id}",
        "task_description": f"Testing consumer health - {datetime.now()}",
        "app_id": 123,
        "compute": [
            {
                "scenario_id": scenario_id,
                "business_type_id": business_type_id,
                "revenue": {"value": 1000, "currency": "USD"},
                "rebate": {"value": 200, "percentage": 20},
                "speciality": {"type": "Cardiology", "region": "US"}
            }
        ]
    }
    
    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        
        if response.status_code == 200:
            task_id = response.json().get("task_id")
            logging.info(f"Created task {task_id} through API")
            
            return {
                "task_id": task_id,
                "scenario_id": scenario_id,
                "business_type_id": business_type_id,
                "partition_key": f"{scenario_id}:{business_type_id}"
            }
        else:
            logging.error(f"Failed to create task through API: {response.status_code} - {response.text}")
            return None
    except Exception as e:
        logging.error(f"Error creating task through API: {str(e)}")
        return None

def check_task_processed(task_info):
    """Check if a task has been processed."""
    logging.info(f"Checking if task {task_info['task_id']} has been processed...")
    
    processed = False
    check_count = 0
    
    while check_count < MAX_CHECKS and not processed:
        try:
            response = requests.get(f"{API_URL}/{task_info['task_id']}", timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                logging.info(f"Task status: {status_data['status']}")
                
                if status_data.get("compute_statuses"):
                    logging.info("Task has been processed!")
                    processed = True
                    return True
            else:
                logging.error(f"Failed to get task status: {response.status_code} - {response.text}")
        except Exception as e:
            logging.error(f"Error checking task status: {str(e)}")
        
        check_count += 1
        if check_count < MAX_CHECKS and not processed:
            logging.info(f"Waiting {CHECK_INTERVAL} seconds before next check...")
            time.sleep(CHECK_INTERVAL)
    
    if not processed:
        logging.warning(f"Task was not processed within {MAX_CHECKS * CHECK_INTERVAL} seconds")
    
    return processed

def main():
    """Main test function."""
    logging.info("Starting consumer health test...")
    
    # Step 1: Check Kafka connectivity
    if not check_kafka_connectivity():
        logging.error("Kafka connectivity check failed. Cannot continue test.")
        sys.exit(1)
    
    # Step 2: Direct message test
    logging.info("\n=== Testing direct Kafka messaging ===")
    direct_message = send_message_directly()
    
    if direct_message:
        message_in_kafka = check_message_in_kafka(direct_message)
        
        if message_in_kafka:
            logging.info(f"Message was successfully written to Kafka partition {direct_message.get('partition', 'unknown')}")
        else:
            logging.warning("Could not verify message in Kafka")
    else:
        logging.error("Failed to send message directly to Kafka")
    
    # Step 3: API message test
    logging.info("\n=== Testing API-based messaging ===")
    api_task = create_task_via_api()
    
    if api_task:
        logging.info(f"Created task through API: {api_task['task_id']}")
        
        # Wait a bit to allow the message to be published to Kafka
        logging.info("Waiting 5 seconds for message to be published...")
        time.sleep(5)
        
        # Check if the message appears in Kafka
        api_task_in_kafka = check_message_in_kafka(api_task)
        
        if api_task_in_kafka:
            logging.info(f"API-created task message found in Kafka partition {api_task.get('partition', 'unknown')}")
        else:
            logging.warning("Could not find API-created task message in Kafka")
    else:
        logging.error("Failed to create task through API")
    
    # Step 4: Check if tasks are processed
    logging.info("\n=== Checking task processing ===")
    
    direct_processed = False
    api_processed = False
    
    if direct_message:
        logging.info("Waiting 5 seconds before checking direct message processing...")
        time.sleep(5)
        
        logging.info("Checking if direct message task is processed...")
        direct_processed = check_task_processed(direct_message)
    
    if api_task:
        logging.info("Checking if API-created task is processed...")
        api_processed = check_task_processed(api_task)
    
    # Summary
    logging.info("\n=== Test Summary ===")
    
    if direct_message:
        logging.info(f"Direct message: {direct_message['task_id']}")
        logging.info(f"  - Published to Kafka: {'Yes' if message_in_kafka else 'No'}")
        logging.info(f"  - Processed: {'Yes' if direct_processed else 'No'}")
    
    if api_task:
        logging.info(f"API-created task: {api_task['task_id']}")
        logging.info(f"  - Published to Kafka: {'Yes' if api_task_in_kafka else 'No'}")
        logging.info(f"  - Processed: {'Yes' if api_processed else 'No'}")
    
    # Final assessment
    if (direct_message and direct_processed) or (api_task and api_processed):
        logging.info("CONCLUSION: Consumer is healthy and processing messages!")
    elif (direct_message and message_in_kafka) or (api_task and api_task_in_kafka):
        logging.info("CONCLUSION: Messages are being sent to Kafka, but not being processed by the consumer.")
    else:
        logging.info("CONCLUSION: Messages are not being sent to Kafka correctly.")

if __name__ == "__main__":
    main() 