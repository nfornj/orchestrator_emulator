import asyncio
import json
import logging
import socket
import time
from confluent_kafka import Producer, Consumer, KafkaException, KafkaError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Kafka configuration from test.py
KAFKA_CONFIG = {
    'bootstrap.servers': 'localhost:9092',  # Use localhost for direct client access
    'security.protocol': 'SASL_PLAINTEXT',          # SASL_PLAINTEXT for emulator
    'sasl.mechanism': 'PLAIN',                      # Authentication mechanism
    'sasl.username': '$ConnectionString',           # Username is always "$ConnectionString"
    'sasl.password': 'Endpoint=sb://eventhubs-emulator:9092;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;UseDevelopmentEmulator=true;Transport=Kafka;',  # Connection string
}

TOPIC_NAME = "orchestrator"  # Event Hub name

def check_connectivity(host, port):
    """Check if the Event Hub emulator is reachable"""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2)
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

def produce_message():
    """Produce a test message to Event Hub using Kafka protocol"""
    logging.info("Attempting to produce a message...")
    
    # First check connectivity
    eventhub_host = "eventhubs-emulator"
    eventhub_port = 9092
    if not check_connectivity(eventhub_host, eventhub_port):
        logging.error("Cannot connect to eventhubs-emulator:9092 - network connectivity issue")
        return False
    
    producer = Producer(KAFKA_CONFIG)
    try:
        test_message = {
            "task_id": "test-task-001",
            "scenario_id": "test-scenario",
            "business_type_id": "test-business-type"
        }
        
        # Create a delivery report callback
        def delivery_report(err, msg):
            if err is not None:
                logging.error(f'Message delivery failed: {err}')
            else:
                logging.info(f'Message delivered to {msg.topic()} [{msg.partition()}]')
        
        # Produce the message
        producer.produce(
            TOPIC_NAME, 
            key="test-key", 
            value=json.dumps(test_message),
            callback=delivery_report
        )
        
        # Wait for any outstanding messages to be delivered
        producer.flush(timeout=10)
        logging.info("Message production attempt completed")
        return True
    except KafkaException as e:
        logging.error(f"Kafka error producing message: {e}")
        return False
    except Exception as e:
        logging.error(f"Unexpected error producing message: {e}")
        return False

def consume_message():
    """Consume messages from Event Hub using Kafka protocol"""
    logging.info("Attempting to consume messages...")
    
    # Configure consumer
    consumer_config = KAFKA_CONFIG.copy()
    consumer_config.update({
        'group.id': 'test-consumer-group',
        'auto.offset.reset': 'earliest',  # Start reading from the beginning
    })
    
    consumer = Consumer(consumer_config)
    consumer.subscribe([TOPIC_NAME])
    
    try:
        # Poll for messages with a timeout
        messages_received = 0
        start_time = time.time()  # Use time.time() instead of asyncio event loop
        
        while time.time() - start_time < 20:  # Try for 20 seconds
            msg = consumer.poll(1.0)
            
            if msg is None:
                continue
                
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    logging.info(f"Reached end of partition: {msg.topic()} [{msg.partition()}]")
                else:
                    logging.error(f"Error consuming message: {msg.error()}")
            else:
                try:
                    value = json.loads(msg.value().decode('utf-8'))
                    logging.info(f"Received message: {value}")
                    messages_received += 1
                except Exception as e:
                    logging.error(f"Error parsing message: {e}")
            
            # Break after receiving at least one message
            if messages_received > 0:
                break
        
        logging.info(f"Consumed {messages_received} messages")
        return messages_received > 0
    finally:
        consumer.close()

if __name__ == "__main__":
    logging.info("Starting Kafka configuration test...")
    
    # Test producing message
    production_success = produce_message()
    
    if production_success:
        # Give some time for the message to be processed
        logging.info("Waiting for message to be processed...")
        time.sleep(2)  # Use regular time.sleep instead of asyncio
        
        # Test consuming message
        consumption_success = consume_message()
        
        if consumption_success:
            logging.info("SUCCESS: Kafka configuration is working properly!")
        else:
            logging.warning("PARTIAL SUCCESS: Produced message, but couldn't consume it")
    else:
        logging.error("FAILED: Could not produce message to Kafka")
    
    logging.info("Kafka configuration test completed") 