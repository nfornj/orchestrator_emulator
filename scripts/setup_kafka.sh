#!/bin/bash

# This script creates the necessary Kafka topics for the application

# Wait for Kafka to be available
echo "Waiting for Kafka to be available..."
until kafka-topics --bootstrap-server kafka:9092 --list &> /dev/null; do
  echo "Waiting for Kafka..."
  sleep 1
done
echo "Kafka is available. Setting up topics..."

# Create topics if they don't exist
echo "Creating orchestrator-events topic..."
kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists \
  --topic orchestrator-events \
  --partitions 1 \
  --replication-factor 1 \
  --config retention.ms=86400000 \
  --config segment.bytes=1073741824

# List the created topics
echo "Available topics:"
kafka-topics --bootstrap-server kafka:9092 --list

echo "Kafka topics setup complete." 