import json
import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient
from httpx import AsyncClient

from app.main import app
from app.services.orchestrator import OrchestratorService
from app.services.event_hub import EventHubProducer, EVENT_HUB_CONNECTION_STR, EVENT_HUB_NAME

# Create test client
client = TestClient(app)


def test_health_endpoint():
    """Test the health endpoint"""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}


def generate_test_payload():
    """Generate a test payload with valid UUIDs"""
    scenario_id = str(uuid.uuid4())
    business_type_id = str(uuid.uuid4())
    
    return {
        "task_name": "Test Task",
        "task_description": "Test Description",
        "payload": [
            {
                "revenue": {
                    "scenario_id": scenario_id,
                    "business_type_id": business_type_id
                },
                "rebates": {
                    "scenario_id": scenario_id,
                    "business_type_id": business_type_id
                },
                "specialty": {
                    "scenario_id": scenario_id,
                    "business_type_id": business_type_id
                }
            }
        ]
    }


@patch("app.api.endpoints.EventHubProducer")
def test_orchestrate_endpoint(mock_producer):
    """Test the orchestrate endpoint that uses Event Hub"""
    # Setup the mock producer
    producer_instance = AsyncMock()
    producer_instance.send_event = AsyncMock(return_value="test-task-id")
    producer_instance.__aenter__.return_value = producer_instance
    mock_producer.return_value = producer_instance
    
    # Make the request
    payload = generate_test_payload()
    response = client.post("/api/orchestrate", json=payload)
    
    # Check response
    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert "task_id" in response.json()
    
    # Verify the producer was called with the right data
    producer_instance.send_event.assert_called_once()


@patch("app.api.endpoints.orchestrator_service")
def test_orchestrate_direct_endpoint(mock_service):
    """Test the direct orchestration endpoint"""
    # Setup the mock service
    mock_service.process_request = AsyncMock(return_value={
        "task_id": "test-task-id",
        "status": "success",
        "results": {"revenue": {"data": []}},
        "errors": {}
    })
    
    # Make the request
    payload = generate_test_payload()
    response = client.post("/api/orchestrate/direct", json=payload)
    
    # Check response
    assert response.status_code == 200
    assert response.json()["status"] == "success"
    assert response.json()["task_id"] == "test-task-id"
    
    # Verify the service was called with the right data
    mock_service.process_request.assert_called_once()


@pytest.mark.asyncio
async def test_orchestrator_service():
    """Test the orchestrator service directly"""
    # Create a test service with mocked external service URLs
    service = OrchestratorService(
        revenue_url="http://mock-revenue",
        rebates_url="http://mock-rebates",
        specialty_url="http://mock-specialty"
    )
    
    # Mock the HTTP client
    with patch("httpx.AsyncClient") as mock_client:
        # Setup the async client mock
        client_instance = AsyncMock()
        mock_client.return_value.__aenter__.return_value = client_instance
        
        # Setup the response mock
        response = MagicMock()
        response.raise_for_status = MagicMock()
        response.json.return_value = {"status": "success", "data": []}
        client_instance.post.return_value = response
        
        # Process a request
        payload = generate_test_payload()
        result = await service.process_request(payload)
        
        # Check result
        assert result["status"] == "success"
        assert "task_id" in result
        assert isinstance(result["results"], dict)
        
        # Verify the client was called for each service
        assert client_instance.post.call_count == 3


def test_invalid_request():
    """Test handling of invalid requests"""
    # Missing required fields
    invalid_payload = {
        "task_name": "Test Task",
        # Missing task_description
        "payload": []  # Empty payload
    }
    
    response = client.post("/api/orchestrate/direct", json=invalid_payload)
    assert response.status_code == 422  # Validation error


@pytest.mark.asyncio
async def test_event_hub_producer():
    """Test the Event Hub producer"""
    # Mock the EventHubProducerClient
    with patch("app.services.event_hub.EventHubProducerClient") as mock_client:
        # Setup the async client mock
        client_instance = AsyncMock()
        mock_client.from_connection_string.return_value = client_instance
        client_instance.__aenter__.return_value = client_instance
        
        # Create test data
        test_data = {"test": "data"}
        
        # Use the producer
        async with EventHubProducer() as producer:
            task_id = await producer.send_event(test_data)
            
            # Verify the producer was called with the right connection string
            mock_client.from_connection_string.assert_called_once_with(
                conn_str=EVENT_HUB_CONNECTION_STR,
                eventhub_name=EVENT_HUB_NAME
            )
            
            # Verify send_batch was called
            assert client_instance.send_batch.called
            
            # Verify we got back a task_id
            assert isinstance(task_id, str) 