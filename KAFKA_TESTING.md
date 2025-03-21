# Kafka Testing Tools for TrueCost Orchestrator

This document describes the tools available for testing the Kafka-based messaging in the TrueCost Orchestrator.

## RedPanda Console

RedPanda Console (formerly known as Kowl) is a web UI for Apache Kafka that allows you to:

- Browse Kafka topics and view messages
- Monitor consumer groups
- Inspect topic configuration
- Create and send messages to topics

### Starting RedPanda Console

To start the RedPanda Console:

```bash
./start_redpanda.sh
```

This script will:

1. Start the RedPanda Console in a Docker container
2. Connect it to your EventHub emulator
3. Optionally run a load test to generate messages

The RedPanda Console will be available at: http://localhost:8085

### Manual Configuration

If you prefer to start RedPanda Console manually:

```bash
docker compose -f docker-compose.redpanda.yml up -d
```

## Load Testing Script

The `test_load.py` script generates test payloads and sends them to the TrueCost Orchestrator API. This helps test the Kafka messaging system by creating real tasks that will be processed through the EventHub/Kafka transport.

### Basic Usage

```bash
./test_load.py
```

This will:

- Generate 100 request payloads with random data
- Send them to the API endpoint at http://localhost:8080/tasks
- Display progress and results
- Save detailed results to a JSON file

### Advanced Options

The script provides several command-line options:

```
-n, --num-requests NUM    Number of requests to send (default: 100)
-c, --concurrency NUM     Max concurrent requests (default: 10)
-v, --verify              Verify task status after creation
-d, --delay SECONDS       Delay between requests in seconds (default: 0)
```

### Example Commands

1. Send 50 requests:

   ```bash
   ./test_load.py -n 50
   ```

2. Higher concurrency (20 parallel requests):

   ```bash
   ./test_load.py -c 20
   ```

3. With status verification:

   ```bash
   ./test_load.py -v
   ```

4. Throttled testing (1 request per second):

   ```bash
   ./test_load.py -d 1
   ```

5. Complete example:
   ```bash
   ./test_load.py -n 200 -c 15 -v -d 0.5
   ```

## Viewing Messages in RedPanda Console

1. Open http://localhost:8085 in your browser
2. Click on the "Topics" tab in the left sidebar
3. Select the "orchestrator" topic
4. View messages in the "Messages" tab

You can:

- Filter messages by key, headers, or content
- View messages in different formats (JSON, Avro, etc.)
- Search for specific content within messages
- See message timestamps and offsets

## Troubleshooting

### RedPanda Console Can't Connect

If RedPanda Console fails to connect to the Kafka broker:

1. Make sure your EventHub emulator is running:

   ```bash
   docker ps | grep eventhubs-emulator
   ```

2. Check the RedPanda Console logs:

   ```bash
   docker logs redpanda-console
   ```

3. Verify the network configuration:
   ```bash
   docker network inspect eh-emulator
   ```

### API Connection Issues

If the load test can't connect to the API:

1. Make sure the API container is running:

   ```bash
   docker ps | grep truecost_orchestrator-api
   ```

2. Check that the port mapping is correct (default: 8080)

   ```bash
   docker compose ps
   ```

3. Try a simple curl request:
   ```bash
   curl http://localhost:8080/health
   ```
