#!/usr/bin/env python3
"""
Check the status of previously created tasks to verify partitioning.
"""
import sys
import json
import requests

# Configuration
API_URL = "http://localhost:8080/tasks"

def get_task_status(task_id):
    """Check the status of a task."""
    response = requests.get(f"{API_URL}/{task_id}")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get task status: {response.status_code} - {response.text}")
        return None

def main():
    # Task IDs from the previous test
    task_ids = [
        "9de6944a-ed08-4af6-869a-77b1abe750f3",  # 1st in sequence
        "36be1e22-d724-430b-aaa9-77b84a3bdfe9",  # 2nd in sequence
        "562bb07f-b441-4831-9fd5-024bf45ae367",  # 3rd in sequence
        "0874a13c-6268-4fc4-8494-b5724055e9b0",  # 4th in sequence
        "4d968f8f-55f1-466c-96dd-5bd0805424c7"   # 5th in sequence (latest)
    ]
    
    print("\nTask processing results:")
    print("=" * 60)
    
    processed_tasks = []
    
    for task_id in task_ids:
        status = get_task_status(task_id)
        if status:
            print(f"Task ID: {task_id}")
            print(f"Status: {status['status']}")
            
            if status.get("compute_statuses"):
                for compute in status["compute_statuses"]:
                    print(f"  Scenario: {compute.get('scenario_id')}")
                    print(f"  Business Type: {compute.get('business_type_id')}")
                    print(f"  Processed At: {compute.get('processed_at')}")
                processed_tasks.append(task_id)
            else:
                print("  No compute statuses found (not processed)")
                
            print("-" * 40)
    
    print("\nVerifying partitioning:")
    print("=" * 60)
    
    if not processed_tasks:
        print("No tasks have been processed yet. Try again later.")
    elif len(processed_tasks) == 1 and processed_tasks[0] == task_ids[-1]:
        print("Only the latest task was processed - partitioning is working correctly!")
    elif len(processed_tasks) == 1:
        print(f"Only task {processed_tasks[0]} was processed, which is not the latest one. Unexpected behavior.")
    elif task_ids[-1] in processed_tasks:
        print("The latest task was processed along with some other tasks. Partitioning may not be fully effective.")
    else:
        print("The latest task was not processed. Unexpected behavior.")

if __name__ == "__main__":
    main() 