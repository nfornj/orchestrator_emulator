#!/usr/bin/env python3
"""
Simple script to test the TrueCost Orchestrator API with maximum diagnostics.
"""
import json
import time
import requests
import sys

# Configuration
API_URL = "http://localhost:8080/tasks"
HEALTH_URL = "http://localhost:8080/health"

def check_health():
    """Check the health of the API"""
    print("Checking API health...")
    try:
        response = requests.get(HEALTH_URL, timeout=5)
        print(f"Health status code: {response.status_code}")
        if response.status_code == 200:
            health_data = response.json()
            print(f"Health data: {json.dumps(health_data, indent=2)}")
            return health_data
        else:
            print(f"Health check failed: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error checking health: {str(e)}")
        return None

def create_task():
    """Create a simple task"""
    payload = {
        "task_name": "Simple Test Task",
        "task_description": "Testing task processing",
        "app_id": 123,
        "compute": [
            {
                "scenario_id": "simple-test-scenario",
                "business_type_id": "simple-test-business",
                "revenue": {"value": 1000, "currency": "USD"},
                "rebate": {"value": 200, "percentage": 20},
                "speciality": {"type": "Cardiology", "region": "US"}
            }
        ]
    }
    
    print(f"Creating task with payload: {json.dumps(payload, indent=2)}")
    try:
        response = requests.post(API_URL, json=payload, timeout=10)
        print(f"Create task status code: {response.status_code}")
        
        if response.status_code == 200:
            task_data = response.json()
            print(f"Created task: {json.dumps(task_data, indent=2)}")
            return task_data.get("task_id")
        else:
            print(f"Failed to create task: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error creating task: {str(e)}")
        return None

def get_task_status(task_id):
    """Check the status of a task with full diagnostics"""
    print(f"Checking status for task {task_id}...")
    try:
        response = requests.get(f"{API_URL}/{task_id}", timeout=10)
        print(f"Status check status code: {response.status_code}")
        
        if response.status_code == 200:
            status_data = response.json()
            print(f"Task status: {json.dumps(status_data, indent=2)}")
            return status_data
        else:
            print(f"Failed to get task status: {response.text}")
            return None
    except requests.exceptions.RequestException as e:
        print(f"Error getting task status: {str(e)}")
        return None

def main():
    """Main function to test task creation and status checking"""
    print("Starting simple API test...")
    print("=" * 60)
    
    # Check API health
    health = check_health()
    if not health or health.get("status") != "ok":
        print("API health check failed. Exiting.")
        sys.exit(1)
    
    # Create a task
    task_id = create_task()
    if not task_id:
        print("Failed to create task. Exiting.")
        sys.exit(1)
    
    print(f"\nTask created with ID: {task_id}")
    print("Monitoring task status...")
    
    # Check status multiple times
    for i in range(5):
        print(f"\nStatus check #{i+1}:")
        print("=" * 40)
        
        status = get_task_status(task_id)
        
        if status and status.get("compute_statuses"):
            print("Task has been processed! ✓")
            break
        
        print("Waiting 3 seconds before next check...")
        time.sleep(3)
    
    print("\nTest completed.")

if __name__ == "__main__":
    main() 