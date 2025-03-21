#!/usr/bin/env python3
"""
A simpler test script for running inside the Docker container to test Kafka connectivity and consumer health.
"""
import json
import uuid
import requests
import time
from datetime import datetime

# Configuration
API_URL = "http://localhost:8080/tasks"  # Use localhost as this will be called from outside the container
MAX_CHECKS = 20
CHECK_INTERVAL = 3

def create_tasks_with_same_partition_key():
    """Create multiple tasks with the same scenario_id and business_type_id."""
    print("Creating tasks with the same partition key...")
    
    # Generate a unique test ID
    test_id = uuid.uuid4().hex[:8]
    scenario_id = f"docker-test-scenario-{test_id}"
    business_type_id = f"docker-test-business-{test_id}"
    
    task_ids = []
    
    # Create multiple tasks with the same scenario_id and business_type_id
    for i in range(1, 3):  # Create 2 tasks
        payload = {
            "task_name": f"Docker Test {i}",
            "task_description": f"Docker testing - sequence {i} - {datetime.now().isoformat()}",
            "app_id": 123,
            "compute": [
                {
                    "scenario_id": scenario_id,
                    "business_type_id": business_type_id,
                    "revenue": {"value": 100 * i, "currency": "USD"},
                    "rebate": {"value": 20 * i, "percentage": 20},
                    "speciality": {"type": "Cardiology", "region": "US"}
                }
            ]
        }
        
        print(f"Creating task {i} with scenario_id={scenario_id}, business_type_id={business_type_id}")
        try:
            response = requests.post(API_URL, json=payload, timeout=10)
            
            if response.status_code == 200:
                task_id = response.json().get("task_id")
                print(f"Created task {task_id}")
                task_ids.append({"task_id": task_id, "sequence": i})
                # Wait a bit between creation to ensure timestamps are different
                time.sleep(1)
            else:
                print(f"Failed to create task: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Error creating task: {str(e)}")
    
    return {
        "task_ids": task_ids,
        "scenario_id": scenario_id,
        "business_type_id": business_type_id
    }

def check_tasks_processed(tasks_info):
    """Check if tasks have been processed."""
    print("\nChecking if tasks have been processed...")
    
    task_ids = tasks_info["task_ids"]
    processed_tasks = []
    check_count = 0
    
    while check_count < MAX_CHECKS and len(processed_tasks) < len(task_ids):
        print(f"\nCheck #{check_count + 1} - Checking task statuses...")
        print("=" * 60)
        
        for task in task_ids:
            task_id = task["task_id"]
            sequence = task["sequence"]
            
            # Skip if already processed
            if any(pt["task_id"] == task_id for pt in processed_tasks):
                print(f"Task #{sequence} (ID: {task_id}) was already processed.")
                continue
                
            try:
                response = requests.get(f"{API_URL}/{task_id}", timeout=10)
                
                if response.status_code == 200:
                    status_data = response.json()
                    print(f"Task #{sequence} (ID: {task_id}) - Status: {status_data['status']}")
                    
                    if status_data.get("compute_statuses"):
                        print(f"  Task #{sequence} has compute statuses - PROCESSED ✓")
                        processed_tasks.append({
                            "task_id": task_id,
                            "sequence": sequence,
                            "status_data": status_data
                        })
                    else:
                        print(f"  Task #{sequence} has no compute statuses - PENDING")
                else:
                    print(f"Failed to get status for task #{sequence}: {response.status_code} - {response.text}")
            except Exception as e:
                print(f"Error checking status for task #{sequence}: {str(e)}")
        
        if processed_tasks:
            # If any task is processed, we can analyze
            break
            
        check_count += 1
        if check_count < MAX_CHECKS:
            print(f"\nWaiting {CHECK_INTERVAL} seconds before next check...")
            time.sleep(CHECK_INTERVAL)
    
    return processed_tasks

def main():
    """Main test function."""
    print("Starting Docker-based consumer health test...")
    
    # Create tasks with same partition key
    tasks_info = create_tasks_with_same_partition_key()
    
    if not tasks_info["task_ids"]:
        print("Failed to create any tasks. Exiting.")
        return
    
    # Wait for tasks to be queued in Kafka
    print("\nWaiting 5 seconds for tasks to be queued in Kafka...")
    time.sleep(5)
    
    # Check if tasks are processed
    processed_tasks = check_tasks_processed(tasks_info)
    
    # Analyze results
    print("\nTest Results:")
    print("=" * 60)
    
    if not processed_tasks:
        print("No tasks were processed during the test period.")
        print("This suggests that the Kafka consumer is not processing messages correctly.")
    elif len(processed_tasks) == 1:
        # Check if it's the latest task (sequence 2)
        if processed_tasks[0]["sequence"] == 2:
            print("SUCCESS: Only the latest task was processed!")
            print(f"Task #{processed_tasks[0]['sequence']} (ID: {processed_tasks[0]['task_id']}) was correctly prioritized.")
            print("The partitioning logic is working correctly - only the latest message for a given partition key was processed.")
        else:
            print(f"UNEXPECTED: Only task #{processed_tasks[0]['sequence']} was processed, which is not the latest one.")
            print("This suggests that the partitioning logic might not be working as expected.")
    else:
        print(f"UNEXPECTED: Multiple tasks ({len(processed_tasks)}/{len(tasks_info['task_ids'])}) were processed.")
        print("In a proper partitioning setup, only the latest task with a given partition key should be processed.")
        print("Processed tasks:")
        for task in processed_tasks:
            print(f"  Task #{task['sequence']}: {task['task_id']}")
    
    print("\nDetails:")
    print(f"Scenario ID: {tasks_info['scenario_id']}")
    print(f"Business Type ID: {tasks_info['business_type_id']}")
    print(f"Partition Key: {tasks_info['scenario_id']}:{tasks_info['business_type_id']}")
    print(f"Created Tasks: {len(tasks_info['task_ids'])}")
    print(f"Processed Tasks: {len(processed_tasks)}")

if __name__ == "__main__":
    main() 