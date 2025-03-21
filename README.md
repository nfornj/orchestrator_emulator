# TrueCost Orchestrator Service

A service for processing compute tasks with scenario-based orchestration.

## Requirements

- Docker and Docker Compose

## Running the Application

1. Start all services:

   ```bash
   docker-compose up -d
   ```

2. To view logs:
   ```bash
   docker-compose logs -f
   ```

## API Endpoints

### Create a Task

```bash
curl -X POST "http://localhost:8080/tasks" \
     -H "Content-Type: application/json" \
     -d '{
           "task_name": "Sample Task",
           "task_description": "Sample Description",
           "app_id": "app12345",
           "compute": [
             {
               "scenario_id": "scenario1",
               "business_type_id": "business1",
               "revenue": 100,
               "rebate": 20,
               "speciality": "Cardiology"
             },
             {
               "scenario_id": "scenario2",
               "business_type_id": "business2",
               "revenue": 200,
               "rebate": 40,
               "speciality": "Oncology"
             }
           ]
         }'
```

### Check Task Status

```bash
curl "http://localhost:8080/tasks/{task_id}"
```

## Kafka Monitoring with RedPanda Console

The application includes the RedPanda Console for monitoring Kafka topics and messages:

1. Access the RedPanda Console UI:

   ```
   http://localhost:8085
   ```

2. View messages in the `orchestrator` topic to monitor task processing.

3. For load testing and generating Kafka messages, use the provided script:
   ```bash
   python test_load.py --requests 100 --concurrency 5
   ```

For more details, see [Kafka Monitoring Documentation](KAFKA_MONITORING.md).

## Architecture

- **FastAPI**: Web framework for API endpoints
- **Redis**: Caching payloads and statuses
- **PostgreSQL**: Persistent storage for task results
- **Azure Event Hubs**: Message queue with partitioning by scenario_id and business_type_id
- **Confluent Kafka**: Client library for EventHub communication
- **RedPanda Console**: UI for monitoring Kafka topics and messages

## Concurrency Handling

- Tasks with the same scenario_id and business_type_id are processed sequentially
- Only the most recent task is processed when multiple tasks have the same scenario_id and business_type_id
