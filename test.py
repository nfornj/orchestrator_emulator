from confluent_kafka import Producer, Consumer, KafkaException, KafkaError
import time

# Kafka configuration for Azure Event Hubs Emulator
KAFKA_CONFIG = {
    'bootstrap.servers': 'localhost:9092',  # Use localhost for direct client access
    'security.protocol': 'SASL_PLAINTEXT',          # Use SASL_PLAINTEXT for emulator; SASL_SSL for Azure Event Hubs
    'sasl.mechanism': 'PLAIN',                      # Authentication mechanism
    'sasl.username': '$ConnectionString',           # Username is always "$ConnectionString"
    'sasl.password': 'Endpoint=sb://eventhubs-emulator:9092;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;UseDevelopmentEmulator=true;Transport=Kafka;',  # Connection string as password
}

TOPIC_NAME = "orchestrator"  # Replace with your Event Hub name

# Function to produce a message
def produce_message():
    """Produce a message to the Event Hub (Kafka topic)."""
    producer = Producer(KAFKA_CONFIG)
    try:
        print("Producing message...")
        producer.produce(TOPIC_NAME, key="key1", value="Hello, Kafka on Event Hubs Emulator!")
        producer.flush()
        print("Message produced successfully.")
    except KafkaException as e:
        print(f"Error producing message: {e}")

# Function to consume a message
def consume_message():
    """Consume a message from the Event Hub (Kafka topic)."""
    consumer_config = KAFKA_CONFIG.copy()
    consumer_config.update({
        'group.id': 'test-consumer-group',
        'auto.offset.reset': 'earliest',  # Start reading from the beginning of the topic
    })

    consumer = Consumer(consumer_config)
    consumer.subscribe([TOPIC_NAME])

    print("Waiting for messages...")
    try:
        while True:
            msg = consumer.poll(1.0)  # Poll for messages with a timeout of 1 second
            if msg is None:
                continue
            if msg.error():
                if msg.error().code() == KafkaError._PARTITION_EOF:
                    # End of partition event
                    print(f"Reached end of partition: {msg.topic()} [{msg.partition()}]")
                elif msg.error():
                    raise KafkaException(msg.error())
            else:
                # Message received successfully
                print(f"Received message: key={msg.key().decode('utf-8')}, value={msg.value().decode('utf-8')}")
                break  # Exit after receiving one message for testing purposes
    finally:
        consumer.close()

if __name__ == "__main__":
    # Produce a message and then consume it
    produce_message()
    time.sleep(2)  # Wait for a moment to ensure the message is available for consumption
    consume_message()
