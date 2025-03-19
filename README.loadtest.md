# Orchestrator Load Testing Tools

This directory contains tools for load testing the Orchestrator API.

## Requirements

- Python 3.7+
- Required Python packages: `httpx`, `asyncio`
- Docker and Docker Compose (for containerized testing)

## Load Testing Scripts

### 1. Python Load Test Script

`load_test.py` is a Python script that sends multiple concurrent requests to the Orchestrator API and measures the response times and success rates.

#### Basic Usage

```bash
# Install dependencies
pip install httpx asyncio

# Run the load test with default parameters (1000 requests, 100 concurrent)
python load_test.py

# Run with custom parameters
python load_test.py --requests 500 --concurrency 50 --url http://localhost:8000/api/orchestrate --check-tasks
```

#### Parameters

- `--url`: The URL of the orchestrator API endpoint (default: http://localhost:8000/api/orchestrate)
- `--requests`: The total number of requests to send (default: 1000)
- `--concurrency`: The maximum number of concurrent requests (default: 100)
- `--check-tasks`: Whether to check the status of tasks after the test (default: False)

### 2. Shell Script Menu

`run_load_test.sh` provides a menu-driven interface for running load tests with different configurations.

```bash
# Make the script executable
chmod +x run_load_test.sh

# Run the script
./run_load_test.sh
```

The menu offers several preset test configurations as well as a custom option.

### 3. Docker-based Load Testing

For containerized environments, you can use the provided Docker and Docker Compose files.

#### Using Docker Directly

```bash
# Build the Docker image
docker build -f Dockerfile.loadtest -t orchestrator-loadtest .

# Run the load test with default parameters
docker run --network orchestrator-network orchestrator-loadtest

# Run with custom parameters
docker run -e API_URL=http://orchestrator:8000/api/orchestrate \
           -e TOTAL_REQUESTS=500 \
           -e CONCURRENCY=50 \
           -e CHECK_TASKS=true \
           --network orchestrator-network \
           orchestrator-loadtest
```

#### Using Docker Compose

```bash
# Run the load test with parameters defined in docker-compose.loadtest.yml
docker-compose -f docker-compose.loadtest.yml up --build

# Run with overridden parameters
TOTAL_REQUESTS=500 CONCURRENCY=50 CHECK_TASKS=true docker-compose -f docker-compose.loadtest.yml up --build
```

## Interpreting Results

The load test output includes:

- **Load Test Summary**: Total requests, success rate, and throughput (requests per second)
- **Response Time Stats**: Min, max, average, median response times, and percentiles (p50, p90, p95, p99)
- **Status Code Distribution**: The distribution of HTTP status codes received
- **Sample Errors**: Sample of any errors encountered during the test
- **Generated Task IDs**: Sample of task IDs created during the test

## Notes on Usage

- Start with smaller tests (e.g., 100 requests) before running larger tests to ensure your system can handle the load.
- The concurrency parameter is important - setting it too high can overwhelm your system.
- For production load testing, consider running the tests from a separate machine to avoid resource contention.
- Use the `--check-tasks` option with smaller tests, as it makes additional API calls to check task statuses.

## Troubleshooting

1. **Connection errors**: Check that the orchestrator service is running and accessible at the specified URL.
2. **Low throughput**: Check if your system has resource constraints (CPU, memory, database connections).
3. **High error rates**: Examine the error messages for clues about what's failing.
