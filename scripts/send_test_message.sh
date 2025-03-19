#!/bin/bash

# This script sends a test message to the Kafka topic

if [ $# -lt 1 ]; then
  echo "Usage: $0 <message payload or file.json>"
  echo "Example: $0 '{\"task_name\":\"Test Task\",\"payload\":[{\"revenue\":{\"scenario_id\":\"550e8400-e29b-41d4-a716-446655440000\"}}]}'"
  echo "Example with file: $0 test_message.json"
  exit 1
fi

TOPIC="orchestrator-events"
MESSAGE=$1

# Check if the argument is a file
if [ -f "$MESSAGE" ]; then
  echo "Reading message from file: $MESSAGE"
  MESSAGE=$(cat "$MESSAGE")
fi

echo "Sending message to topic $TOPIC:"
echo "$MESSAGE"

echo "$MESSAGE" | docker exec -i kafka kafka-console-producer \
  --bootstrap-server kafka:9092 \
  --topic $TOPIC

echo "Message sent to Kafka topic $TOPIC" 