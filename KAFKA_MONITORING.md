# Kafka Monitoring with RedPanda Console

This document explains how to use the RedPanda Console to monitor Kafka topics and messages in the TrueCost Orchestrator application.

## Overview

RedPanda Console is a web UI for monitoring and managing Kafka clusters. It's integrated directly into the main `docker-compose.yml` file, making it easy to use alongside the rest of the application.

## Getting Started

1. Start your application normally using:

   ```
   docker-compose up -d
   ```

2. Access the RedPanda Console at:
   ```
   http://localhost:8085
   ```

## Features

The RedPanda Console offers several useful features:

- **Topic Viewer**: Browse topics and view messages in real-time
- **Consumer Groups**: Monitor consumer group offsets and lag
- **Schema Registry**: View and manage schemas (if enabled)
- **Topic Creation**: Create new topics with custom settings

## Monitoring Orchestrator Events

The primary topic used by the TrueCost Orchestrator is `orchestrator`. This is where task events are published and consumed.

To view messages:

1. In the RedPanda Console, navigate to the "Topics" section
2. Click on the `orchestrator` topic
3. Use the "Messages" tab to view the messages in the topic
4. You can filter messages, format them as JSON, and see message metadata

## Troubleshooting

### Connection Issues

If RedPanda cannot connect to the Kafka broker:

1. Ensure the EventHub emulator is running
2. Check the SASL configuration in `redpanda-config.yml`
3. Verify network connectivity between containers
4. Check the RedPanda Console logs:
   ```
   docker logs redpanda-console
   ```

### Message Viewing Issues

If messages don't appear or are improperly formatted:

1. Verify that messages are being produced to the topic
2. Try adjusting message display settings in the console
3. Check if the payload format is one that RedPanda can display correctly

## Advanced Usage

### Custom Filters

You can set up custom filters to monitor specific message patterns:

1. In the message viewer, click on "Filter"
2. Create filters based on JSON field values, timestamps, or other criteria

### Message Publishing

You can publish test messages directly from the RedPanda Console:

1. Navigate to the desired topic
2. Click on "Publish Message"
3. Enter the message payload (JSON format)
4. Click "Publish"
