#!/bin/bash

# Exit on error
set -e

# Get the absolute path to the script directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )"

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "Error: Docker is not running. Please start Docker and try again."
    exit 1
fi

# Function to clean up containers in case of failure
cleanup() {
    echo "Cleaning up containers..."
    
    # Stop and remove containers with docker compose
    echo "Stopping and removing containers..."
    docker compose down || true
    
    echo "Cleanup complete."
}

# Set up trap to clean up on exit
trap cleanup ERR

# Ensure network exists
echo "Ensuring network exists..."
if ! docker network ls | grep -q eh-emulator-network; then
    echo "Creating network: eh-emulator-network"
    docker network create eh-emulator-network
    echo "Network created."
else
    echo "Network eh-emulator-network already exists."
fi

# Remove orphaned containers
echo "Removing any orphaned containers..."
docker compose down --remove-orphans

# Start Azurite first and wait for it to be ready
echo "Starting Azurite storage emulator..."
docker compose up -d azurite

# Wait for Azurite to be ready
echo "Waiting for Azurite to be ready..."
sleep 5

# Check if Azurite container is running
if ! docker compose ps | grep -q "azurite.*Up"; then
    echo "Error: Azurite container is not running"
    echo "Container logs:"
    docker compose logs azurite
    cleanup
    exit 1
fi

# Test Azurite endpoints
echo "Testing Azurite endpoints..."
if ! curl -s -o /dev/null -w "%{http_code}" http://localhost:10000/ | grep -q "200\|400\|404"; then
    echo "Error: Azurite blob endpoint is not responding"
    docker compose logs azurite
    cleanup
    exit 1
fi

echo "Azurite is running and responding."

# Start Zookeeper
echo "Starting Zookeeper..."
docker compose up -d zookeeper

# Wait for Zookeeper to be ready
echo "Waiting for Zookeeper to be ready..."
sleep 5

# Check if Zookeeper container is running
if ! docker compose ps | grep -q "zookeeper.*Up"; then
    echo "Error: Zookeeper container is not running"
    echo "Container logs:"
    docker compose logs zookeeper
    cleanup
    exit 1
fi

# Start Kafka
echo "Starting Kafka..."
docker compose up -d kafka

# Wait for Kafka to be ready
echo "Waiting for Kafka to be ready..."
sleep 10

# Check if Kafka container is running
if ! docker compose ps | grep -q "kafka.*Up"; then
    echo "Error: Kafka container is not running"
    echo "Container logs:"
    docker compose logs kafka
    cleanup
    exit 1
fi

# Create the Kafka topic if it doesn't exist
echo "Creating Kafka topic if it doesn't exist..."
docker exec -i kafka kafka-topics --create --if-not-exists --topic orchestrator-events --bootstrap-server kafka:9092 --partitions 3 --replication-factor 1

echo "Kafka, Zookeeper, and Azurite are running."
echo "To view logs: docker compose logs -f kafka"
echo "To stop: docker compose down"
echo ""
echo "----------------------------------------------------------------------------------------"
echo "KAFKA CONNECTION INFORMATION"
echo "----------------------------------------------------------------------------------------"
echo "Kafka bootstrap servers for Docker containers:"
echo "kafka:9092"
echo ""
echo "Kafka bootstrap servers for local development:"
echo "localhost:9093"
echo ""
echo "Kafka topic: orchestrator-events"
echo "----------------------------------------------------------------------------------------"

# Display port bindings for verification
echo ""
echo "Current container port bindings:"
docker container ls --format "{{.Names}}: {{.Ports}}" 