import json
import logging
import requests
import time

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# API base URL
API_BASE_URL = "http://host.docker.internal:8080"  # Use host.docker.internal to access the host machine from container

# Test task payload
test_payload = {
    "task_name": "Test Task",
    "task_description": "Test EventHub integration",
    "app_id": 123,
    "compute": [
        {
            "scenario_id": "test_scenario_1",
            "business_type_id": "test_business_1",
            "revenue": {"value": 1000},
            "rebate": {"value": 100},
            "speciality": {"type": "test"}
        },
        {
            "scenario_id": "test_scenario_2",
            "business_type_id": "test_business_2",
            "revenue": {"value": 2000},
            "rebate": {"value": 200},
            "speciality": {"type": "test"}
        }
    ]
}

def test_health_endpoint():
    """Test the health endpoint to check EventHub connectivity"""
    logging.info("Testing health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/health")
        logging.info(f"Health check response: {response.json()}")
        
        assert response.status_code == 200
        assert response.json()["status"] in ["ok", "degraded"]
        
        # If EventHub is properly connected, we should see "ok" status
        if response.json()["services"]["eventhub"] == "ok":
            logging.info("EventHub connection is healthy!")
        else:
            logging.warning(f"EventHub connection issue: {response.json()['services']['eventhub']}")
        
        return True
    except Exception as e:
        logging.error(f"Error testing health endpoint: {e}")
        return False

def test_create_task():
    """Test task creation and EventHub message sending"""
    logging.info("Testing task creation endpoint...")
    try:
        response = requests.post(f"{API_BASE_URL}/tasks", json=test_payload)
        
        assert response.status_code == 200
        assert "task_id" in response.json()
        
        task_id = response.json()["task_id"]
        logging.info(f"Created task with ID: {task_id}")
        
        # Wait for event processing
        logging.info("Waiting for EventHub processing...")
        time.sleep(3)
        
        # Check task status
        status_response = requests.get(f"{API_BASE_URL}/tasks/{task_id}")
        logging.info(f"Task status response: {status_response.json()}")
        
        assert status_response.status_code == 200
        assert status_response.json()["task_id"] == task_id
        
        return task_id
    except Exception as e:
        logging.error(f"Error testing task creation: {e}")
        return None

if __name__ == "__main__":
    logging.info("Starting EventHub integration tests...")
    
    # Test health endpoint
    health_check_success = test_health_endpoint()
    
    if health_check_success:
        # Test task creation and processing
        task_id = test_create_task()
        
        if task_id:
            logging.info("EventHub integration tests completed successfully!")
        else:
            logging.error("Task creation test failed!")
    else:
        logging.error("Health check failed!") 