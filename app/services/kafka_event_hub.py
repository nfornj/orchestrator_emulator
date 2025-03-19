import os
import json
import logging
import uuid
from typing import Dict, List, Any, Optional
import asyncio
from confluent_kafka import Producer, Consumer, KafkaError, KafkaException
import socket

from app.event_hub import UUIDEncoder

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_kafka_config() -> Dict[str, Any]:
    """
    Get the Kafka configuration from environment variables.
    
    Returns:
        Dict[str, Any]: Kafka configuration
    """
    bootstrap_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
    topic = os.environ.get('KAFKA_TOPIC', 'orchestrator-events')
    
    logger.info(f"Using Kafka bootstrap servers: {bootstrap_servers}")
    logger.info(f"Using Kafka topic: {topic}")
    
    return {
        'bootstrap_servers': bootstrap_servers,
        'topic': topic
    }

class KafkaEventHubProducer:
    """
    Kafka implementation of the Event Hub producer.
    """
    
    def __init__(self):
        """
        Initialize the Kafka producer.
        """
        self.bootstrap_servers = os.environ.get('KAFKA_BOOTSTRAP_SERVERS', 'kafka:9092')
        self.topic = os.environ.get('KAFKA_TOPIC', 'orchestrator-events')
        
        # Create Kafka producer configuration
        self.producer_config = {
            'bootstrap.servers': self.bootstrap_servers,
            'client.id': socket.gethostname()
        }
        
        # Create Kafka producer
        try:
            self.producer = Producer(self.producer_config)
            logger.info(f"Initialized Kafka producer with bootstrap servers: {self.bootstrap_servers}")
        except Exception as e:
            logger.error(f"Failed to initialize Kafka producer: {str(e)}")
            raise
    
    async def __aenter__(self):
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        # Ensure all messages are sent before closing
        self.producer.flush()
    
    def _delivery_report(self, err, msg):
        """
        Callback function for message delivery reports.
        
        Args:
            err: Error (if any)
            msg: Message that was delivered
        """
        if err is not None:
            logger.error(f"Message delivery failed: {err}")
        else:
            logger.debug(f"Message delivered to {msg.topic()} [{msg.partition()}] at offset {msg.offset()}")
    
    async def send_event(self, event_data: Dict[str, Any]) -> str:
        """
        Send an event to the Kafka topic.
        
        Args:
            event_data: The event data to send
            
        Returns:
            The ID of the event (same as task_id)
        """
        try:
            # Use task_id from event_data if available, otherwise generate a new one
            task_id = event_data.get("task_id", str(uuid.uuid4()))
            
            # Add task_id to event data if not present
            if "task_id" not in event_data:
                event_data["task_id"] = task_id
            
            # Convert event data to JSON with custom UUID encoder
            event_json = json.dumps(event_data, cls=UUIDEncoder)
            
            # Send message to Kafka
            self.producer.produce(
                self.topic,
                value=event_json.encode('utf-8'),
                callback=self._delivery_report,
                key=str(task_id).encode('utf-8')  # Use task_id as the message key
            )
            
            # Trigger any available delivery callbacks
            self.producer.poll(0)
            
            logger.info(f"Sent event to Kafka topic {self.topic} with task_id: {task_id}")
            
            return task_id
            
        except Exception as e:
            logger.error(f"Error sending event to Kafka: {str(e)}")
            raise

class KafkaEventHubConsumer:
    """
    Kafka consumer for receiving events.
    """
    
    def __init__(self, consumer_group: str = 'orchestrator-consumer-group'):
        """
        Initialize the Kafka consumer.
        
        Args:
            consumer_group (str): Consumer group name
        """
        kafka_config = get_kafka_config()
        self.topic = kafka_config['topic']
        
        # Configure the Kafka consumer
        conf = {
            'bootstrap.servers': kafka_config['bootstrap_servers'],
            'group.id': consumer_group,
            'auto.offset.reset': 'earliest',
            'enable.auto.commit': True,
            'error_cb': self._on_kafka_error,
            'security.protocol': 'PLAINTEXT'
        }
        
        try:
            self.consumer = Consumer(conf)
            self.consumer.subscribe([self.topic])
            logger.info(f"Kafka consumer subscribed to topic: {self.topic}")
        except KafkaException as e:
            logger.error(f"Failed to initialize Kafka consumer: {e}")
            raise
    
    def _on_kafka_error(self, error):
        """
        Handle Kafka errors.
        
        Args:
            error: Kafka error
        """
        logger.error(f"Kafka error: {error}")
    
    async def start_receiving(self, callback):
        """
        Start receiving events from the Kafka topic.
        
        Args:
            callback: Callback function to process events
        """
        logger.info(f"Starting to receive events from Kafka topic: {self.topic}")
        
        try:
            while True:
                try:
                    # Poll for messages
                    msg = self.consumer.poll(1.0)
                    
                    if msg is None:
                        # No message available within timeout
                        await asyncio.sleep(0.1)
                        continue
                    
                    if msg.error():
                        if msg.error().code() == KafkaError._PARTITION_EOF:
                            # End of partition event
                            logger.debug(f"Reached end of partition {msg.partition()}")
                        else:
                            # Error
                            logger.error(f"Error while consuming: {msg.error()}")
                    else:
                        # Parse the message value
                        try:
                            event_data = json.loads(msg.value().decode('utf-8'))
                            
                            # Call the callback with the event data
                            # Use asyncio.create_task to avoid blocking
                            asyncio.create_task(callback(event_data))
                        except json.JSONDecodeError as e:
                            logger.error(f"Failed to parse event data: {e}")
                        except Exception as e:
                            logger.error(f"Error processing event: {e}")
                
                except Exception as e:
                    logger.error(f"Error in Kafka consumer loop: {e}")
                    await asyncio.sleep(1)  # Sleep before retrying
        
        except Exception as e:
            logger.error(f"Error starting Kafka consumer: {e}")
            raise
        finally:
            # Close the consumer on exit
            self.consumer.close()
            logger.info("Kafka consumer closed") 