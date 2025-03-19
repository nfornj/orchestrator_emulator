# Orchestrator Service with Kafka

This project implements an Orchestrator service using FastAPI, Kafka, and Docker. The Orchestrator processes incoming JSON payloads by splitting them and asynchronously calling external services.

## Architecture

The architecture consists of:

- **FastAPI Application**: Exposes REST endpoints and handles the API communication
- **Kafka**: Manages the queue of incoming requests for asynchronous processing
- **PostgreSQL Database**: Stores task tracking information and service request status
- **Orchestrator Service**: Core business logic for splitting payloads and async processing
- **External Services**: Mock implementations of `/revenue`, `/rebates`, and `/specialty` services

## Prerequisites

- Docker and Docker Compose
- Python 3.8+

## Project Structure

```
orchestrator_emulator/
├── app/
│   ├── api/                    # API endpoints
│   ├── models/                 # Database models
│   │   └── task_tracking.py    # Task and service request models
│   ├── schemas/                # Pydantic schemas
│   │   └── task_tracking.py    # Task and service request schemas
│   ├── services/               # Core services
│   │   ├── event_hub.py        # AMQP-based Event Hub client (legacy)
│   │   ├── kafka_event_hub.py  # Kafka-based event processing
│   │   ├── http_event_hub.py   # HTTP-based event processing (alternative)
│   │   ├── task_tracking.py    # Database task tracking service
│   │   └── orchestrator.py     # Core orchestration logic
│   ├── database.py             # Database connection setup
│   ├── models.py               # API Pydantic models
│   └── main.py                 # FastAPI application
├── migrations/                 # Alembic database migrations
│   └── versions/               # Migration scripts
├── mock-services/              # Mock implementations of external services
├── run_emulator.sh             # Helper script to run Kafka and other services
├── Dockerfile                  # Docker configuration for the orchestrator
├── docker-compose.yml          # Docker Compose configuration
└── requirements.txt            # Python dependencies
```

## Setup & Running

### Using Docker Compose (Recommended)

1. Clone the repository:

   ```bash
   git clone <repository-url>
   cd orchestrator_emulator
   ```

2. Use the provided script to start Kafka and other services:

   ```bash
   ./run_emulator.sh
   ```

   This will automatically:

   - Create the required Docker network if it doesn't exist
   - Pull the necessary Docker images
   - Start Kafka, Zookeeper, and Azurite containers
   - Create the required Kafka topic
   - Verify that the containers are running correctly

3. Start the complete application:

   ```bash
   docker compose up -d orchestrator
   ```

   This will start:

   - The orchestrator service on port 8000
   - Kafka and Zookeeper for message queueing
   - Azurite (Azure Storage emulator)
   - Mock services on ports 8001, 8002, and 8003

4. Access the API documentation at http://localhost:8000/docs

### Local Development

1. Install dependencies:

   ```bash
   pip install -r requirements.txt
   ```

2. Start Kafka and other services:

   ```bash
   ./run_emulator.sh
   ```

3. Set up environment variables (or create a `.env` file):

   ```
   USE_KAFKA=True
   KAFKA_BOOTSTRAP_SERVERS=localhost:9093
   KAFKA_TOPIC=orchestrator-events
   EVENT_HUB_NAME=orchestrator-events
   STORAGE_CONNECTION_STRING=DefaultEndpointsProtocol=http;AccountName=devstoreaccount1;AccountKey=Eby8vdM02xNOcqFlqUwJPLlmEtlCDXJ1OUzFT50uSRZ6IFsuFq2UVErCz4I6tq/K1SZFPTOtr/KBHBeksoGMGw==;BlobEndpoint=http://127.0.0.1:10000/devstoreaccount1;
   ```

4. Run the mock services:

   ```bash
   cd mock-services
   uvicorn app:app --host 0.0.0.0 --port 8001
   # In separate terminals:
   uvicorn app:app --host 0.0.0.0 --port 8002
   uvicorn app:app --host 0.0.0.0 --port 8003
   ```

5. Run the FastAPI application:
   ```bash
   uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
   ```

## API Endpoints

### 1. `/api/orchestrate` (POST)

Accepts orchestration requests and sends them to Kafka for asynchronous processing.

Example request:

```json
{
  "task_name": "Compute Financial Metrics",
  "task_description": "Compute revenue, rebates, and specialty metrics for the given scenarios",
  "payload": [
    {
      "revenue": {
        "scenario_id": "123e4567-e89b-12d3-a456-426614174000",
        "business_type_id": "123e4567-e89b-12d3-a456-426614174001"
      },
      "rebates": {
        "scenario_id": "123e4567-e89b-12d3-a456-426614174000",
        "business_type_id": "123e4567-e89b-12d3-a456-426614174001"
      },
      "specialty": {
        "scenario_id": "123e4567-e89b-12d3-a456-426614174000",
        "business_type_id": "123e4567-e89b-12d3-a456-426614174001"
      }
    }
  ]
}
```

### 2. `/api/orchestrate/direct` (POST)

Directly processes orchestration requests without using Kafka (for testing).

### 3. `/api/tasks` (GET)

Retrieves a list of all tasks and their status.

### 4. `/api/tasks/{task_id}` (GET)

Retrieves detailed information about a specific task, including its service requests.

### 5. `/health` (GET)

Health check endpoint. Returns the current event processing mode (kafka, http, or amqp).

## Database Configuration

The application uses PostgreSQL for task tracking. The database stores information about tasks and their associated service requests, allowing you to monitor the status of processing requests.

### Database Schema

- **Tasks**: Stores information about orchestration tasks

  - `id`: Unique identifier
  - `task_id`: UUID string identifier
  - `task_name`: Name of the task
  - `task_description`: Description of the task
  - `status`: Current status (PENDING, IN_PROGRESS, COMPLETED, FAILED)
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp
  - `payload`: JSON payload of the request
  - `error_message`: Error message if the task failed

- **Service Requests**: Stores information about individual service requests within a task
  - `id`: Unique identifier
  - `task_id`: Reference to the parent task
  - `service_name`: Name of the service (revenue, rebates, specialty)
  - `scenario_id`: Scenario identifier
  - `business_type_id`: Business type identifier
  - `status`: Current status (PENDING, IN_PROGRESS, COMPLETED, FAILED)
  - `created_at`: Creation timestamp
  - `updated_at`: Last update timestamp
  - `request_payload`: JSON payload sent to the service
  - `response_payload`: JSON response from the service
  - `error_message`: Error message if the service request failed

### Database Connection

The database connection string is configured through the `DATABASE_URL` environment variable:

```
DATABASE_URL=postgresql://postgres:postgres@postgres:5432/orchestrator
```

For local development outside Docker, use:

```
DATABASE_URL=postgresql://postgres:postgres@localhost:5432/orchestrator
```

### Migrations

Database migrations are managed with Alembic. The migrations are automatically applied when the application starts. If you need to run them manually:

```bash
# Initialize the database
alembic upgrade head

# Create a new migration
alembic revision --autogenerate -m "Description of changes"
```

## Kafka Configuration

This project uses a standard Kafka setup with Zookeeper for local development.

### Connection Options:

#### For Docker Containers

Use these settings in your Dockerfile or docker-compose.yml:

```yaml
environment:
  - USE_KAFKA=True
  - KAFKA_BOOTSTRAP_SERVERS=kafka:9092
  - KAFKA_TOPIC=orchestrator-events
```

#### For Local Development

Use these settings when running the application outside Docker:

```
USE_KAFKA=True
KAFKA_BOOTSTRAP_SERVERS=localhost:9093
KAFKA_TOPIC=orchestrator-events
```

### Troubleshooting

If you encounter connection issues:

1. Verify that Kafka and Zookeeper are running:

   ```bash
   docker compose ps
   ```

2. Check the Kafka logs:

   ```bash
   docker compose logs kafka
   ```

3. Verify the Kafka topic exists:

   ```bash
   docker exec -it kafka kafka-topics --list --bootstrap-server kafka:9092
   ```

4. Test producing a message to Kafka:

   ```bash
   docker exec -it kafka kafka-console-producer --topic orchestrator-events --bootstrap-server kafka:9092
   ```

5. Test consuming messages from Kafka:
   ```bash
   docker exec -it kafka kafka-console-consumer --topic orchestrator-events --from-beginning --bootstrap-server kafka:9092
   ```

### Setting up for production:

1. Set up a production Kafka cluster (e.g., using Confluent Cloud, AWS MSK, or your own Kafka deployment).
2. Update the connection settings to use your production Kafka bootstrap servers.
3. Configure authentication and TLS encryption as needed for your production environment.

## Error Handling

The service implements robust error handling:

- Input validation using Pydantic models
- Graceful handling of service failures
- Detailed logging for diagnostic purposes
- Retries for temporary failures

## Running Tests

```bash
pytest
```

## Production Deployment

For production deployment:

1. Replace the Event Hub emulator with a real Azure Event Hub.
2. Configure proper authentication and security settings.
3. Set up monitoring and alerting.
4. Consider using Azure Container Instances or Kubernetes for orchestration.

## License

[Include license information here]
