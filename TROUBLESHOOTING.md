# Troubleshooting Guide

## Docker Network Issues

### Error: Network not found

If you see an error like:

```
Error response from daemon: network 7e9cdb0362bbfdd4789bd6a4cf46a01d4ba0d3b121b94a3406cbb7f9b24f6a79 not found
```

This typically occurs when:

1. The Docker network was deleted while containers were still using it
2. There's a mismatch between network names in `docker-compose.yml` and actual networks
3. Docker has an internal error tracking networks

### Docker Compose Network Warning

If you see a warning like:

```
WARN[0000] a network with name eh-emulator-network exists but was not created by compose.
Set `external: true` to use an existing network
network eh-emulator-network was found but has incorrect label com.docker.compose.network set to "" (expected: "eh-emulator-network")
```

This warning appears when:

1. The network was created manually (not by Docker Compose)
2. The network in docker-compose.yml is not marked as `external: true`

This has been fixed in the configuration by:

1. Marking the network as `external: true` in docker-compose.yml
2. Creating the network before running Docker Compose in run_emulator.sh

## Event Hub Emulator Issues

### Error: Consumer group $default is internally created

If you see an error like:

```
Unhandled exception. FluentAssertions.Execution.AssertionFailedException: Expected string not to be equivalent to "$default" because Consumer group $default is internally created., but they are.
```

This error occurs when:

1. Your config.json file explicitly defines a consumer group named "$Default" or "$default"
2. The emulator rejects this because the "$default" consumer group is automatically created by the Event Hub service

Resolution:

1. Edit your config.json file
2. Remove any consumer group with the name "$Default" from the ConsumerGroups array
3. The emulator will automatically create the $default consumer group
4. Restart the emulator with `./run_emulator.sh`

### Error: Connection refused to Event Hub emulator

If you see errors like:

```
Transport connect failed: ConnectionRefusedError(111, 'Connection refused')
Failed to initiate the connection due to exception: [Errno 111] Connection refused
```

This indicates that:

1. The Event Hub emulator is not listening on port 5672 (AMQP port)
2. The port mappings in the docker-compose.yml file might be incorrect
3. The emulator might have started but is not fully operational

Resolution:

1. Check the emulator logs: `docker compose logs emulator`
2. Verify that the emulator shows "Emulator Service is Successfully Up!"
3. Ensure port 5672 is correctly exposed in docker-compose.yml
4. **Switch to Kafka protocol** by setting `USE_KAFKA=True` in your environment or docker-compose.yml
5. Try the following troubleshooting steps:

   ```bash
   # Stop all containers
   docker compose down

   # Remove any stale containers
   docker compose rm -f

   # Restart with fresh state
   ./run_emulator.sh

   # Check port bindings
   docker container ls --format "{{.Names}}: {{.Ports}}"

   # For AMQP connectivity test (likely to fail if you're having issues)
   docker exec -it orchestrator curl -v telnet://emulator:5672

   # For Kafka connectivity test
   docker exec -it orchestrator curl -v telnet://emulator:9092
   ```

6. If metadata store issues persist, check your environment variables:

   ```
   BLOB_SERVER: "azurite:10000"
   METADATA_SERVER: "azurite:10002"
   ```

### Known Issue: Event Hub Emulator AMQP Port Not Available

The Event Hub emulator appears to have a known issue where the AMQP port (5672) isn't properly accessible despite the container being up and running. This issue can manifest as continuous "Connection refused" errors.

Possible causes and solutions:

1. **Official Emulator Limitation**: The official Microsoft Azure Event Hub emulator may have limitations with the AMQP protocol in containerized environments.

2. **Port Binding Issues**: Although ports are properly mapped (as shown by `docker container ls`), the emulator may not be binding to all interfaces (0.0.0.0) correctly.

3. **Connection String Format**: Try different connection string formats:

   ```
   # Option 1 (with port)
   Endpoint=sb://eventhubs-emulator:5672;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=emulatorKey;UseDevelopmentEmulator=true;

   # Option 2 (without port)
   Endpoint=sb://eventhubs-emulator;SharedAccessKeyName=RootManageSharedAccessKey;SharedAccessKey=emulatorKey;UseDevelopmentEmulator=true;
   ```

4. **Docker Desktop Settings**: Try increasing the resources allocated to Docker Desktop.

5. **Alternative Approach**: Use the Kafka protocol instead of AMQP by setting `USE_KAFKA=True` in your environment or docker-compose.yml.

6. **Report to Microsoft**: If the issue persists, consider reporting it to Microsoft's Azure Event Hub emulator team through their GitHub repository.

### Kafka Protocol Issues

If you switched to Kafka but are still experiencing connection issues:

1. **Check Kafka Port**: Ensure port 9092 is correctly exposed in your docker-compose.yml:

   ```yaml
   ports:
     - "9092:9092" # Kafka port
   ```

2. **Verify Kafka Configuration**:

   - In docker-compose.yml, ensure you have the correct environment variables:
     ```yaml
     environment:
       - USE_KAFKA=True
       - KAFKA_BOOTSTRAP_SERVERS=eventhubs-emulator:9092
       - KAFKA_TOPIC=orchestrator-events
     ```
   - For local development:
     ```
     USE_KAFKA=True
     KAFKA_BOOTSTRAP_SERVERS=localhost:9092
     KAFKA_TOPIC=orchestrator-events
     ```

3. **Check Kafka is Enabled in the Emulator**:
   The emulator should automatically support Kafka, but check the logs:

   ```bash
   docker compose logs emulator | grep -i kafka
   ```

4. **Verify Kafka Dependencies**:
   Make sure the Dockerfile includes necessary dependencies:

   ```
   RUN apt-get update && apt-get install -y \
       build-essential \
       librdkafka-dev
   ```

5. **Restart the Application**: After making any changes, restart all containers:
   ```bash
   docker compose down
   ./run_emulator.sh
   docker compose up -d orchestrator
   ```

### Resolution Steps

1. **Reset the environment completely**:

   ```bash
   # Stop all containers
   docker compose down

   # If you need to completely reset the network:
   docker network rm eh-emulator-network
   ```

2. **Restart Docker** (if problems persist):

   - On Mac: Quit Docker Desktop and restart it
   - On Linux: `sudo systemctl restart docker`
   - On Windows: Restart Docker Desktop

3. **Run the emulator setup script**:
   ```bash
   ./run_emulator.sh
   ```
   This script will now automatically:
   - Check if the network exists and create it if necessary
   - Use Docker Compose with the external network configuration
   - Handle errors gracefully

## Connection Issues

If your Orchestrator Service can't connect to the Event Hub emulator:

1. Verify containers are running on the same network:

   ```bash
   docker network inspect eh-emulator-network
   ```

   This should list all containers connected to this network.

2. Check container logs:

   ```bash
   docker compose logs orchestrator
   docker compose logs emulator
   ```

3. Ensure connection strings are correct:

   - For container-to-container: `Endpoint=sb://eventhubs-emulator;...`
   - For local development: `Endpoint=sb://localhost;...`
   - Or for Kafka: `KAFKA_BOOTSTRAP_SERVERS=eventhubs-emulator:9092`

4. Test network connectivity from inside the container:
   ```bash
   docker exec -it orchestrator ping emulator
   ```
   This should succeed if network resolution is working correctly.

## Docker Compose Issues

If `docker compose` commands fail:

1. Check Docker and Docker Compose versions:

   ```bash
   docker --version
   docker compose version
   ```

2. Ensure the `.env` file exists and has correct variables:

   ```bash
   cat .env
   ```

3. Validate your docker-compose.yml syntax:
   ```bash
   docker compose config
   ```

## Getting Help

If you're still experiencing issues:

1. Gather diagnostic information:

   ```bash
   docker info
   docker system info
   docker network ls
   docker ps -a
   docker compose ps
   ```

2. Check Docker logs:

   ```bash
   docker system events --since 1h
   ```

3. Include this information when seeking help from the team.
