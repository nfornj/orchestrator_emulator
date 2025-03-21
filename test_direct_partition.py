#!/usr/bin/env python3
"""
Test script to verify direct partitioning in TrueCost Orchestrator.
Since Kafka connection is failing, this test manually implements a partitioning-like
approach to demonstrate the concept.
"""
import argparse
import json
import time
import uuid
import requests
from datetime import datetime
import asyncio
import sys

# Configuration
API_URL = "http://localhost:8080/tasks"
MAX_RETRIES = 3
RETRY_DELAY = 1

def create_task(scenario_id, business_type_id, sequence_num):
    """Create a task with the specified scenario_id and business_type_id."""
    timestamp = datetime.now().isoformat()
    
    payload = {
        "task_name": f"Direct Partition Test {sequence_num}",
        "task_description": f"Testing direct partitioning - sequence {sequence_num} - {timestamp}",
        "app_id": 123,
        "compute": [
            {
                "scenario_id": scenario_id,
                "business_type_id": business_type_id,
                "revenue": {"value": 100 * sequence_num, "currency": "USD"},
                "rebate": {"value": 20 * sequence_num, "percentage": 20},
                "speciality": {"type": "Cardiology", "region": "US"}
            }
        ]
    }
    
    print(f"Creating task with scenario_id={scenario_id}, business_type_id={business_type_id}, sequence={sequence_num}")
    
    # Try with retries
    for retry in range(MAX_RETRIES):
        try:
            response = requests.post(API_URL, json=payload, timeout=10)
            response.raise_for_status()
            
            task_id = response.json().get("task_id")
            print(f"Created task {task_id}")
            return {
                "task_id": task_id,
                "timestamp": timestamp,
                "sequence": sequence_num
            }
        except requests.exceptions.RequestException as e:
            print(f"Attempt {retry+1}/{MAX_RETRIES} failed: {str(e)}")
            if retry < MAX_RETRIES - 1:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                print("All retries failed")
                return None

def get_task_status(task_id):
    """Check the status of a task."""
    print(f"Checking status for task {task_id}...")
    
    # Try with retries
    for retry in range(MAX_RETRIES):
        try:
            response = requests.get(f"{API_URL}/{task_id}", timeout=10)
            response.raise_for_status()
            
            status_data = response.json()
            print(f"Raw API response: {json.dumps(status_data, indent=2)}")
            return status_data
        except requests.exceptions.RequestException as e:
            print(f"Attempt {retry+1}/{MAX_RETRIES} failed: {str(e)}")
            if retry < MAX_RETRIES - 1:
                print(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                print("All retries failed")
                return None

def simulate_partitioning(tasks):
    """Simulate the partitioning logic that would be applied by Kafka."""
    # Sort tasks by timestamp (newest first)
    sorted_tasks = sorted(tasks, key=lambda x: x["timestamp"], reverse=True)
    
    # In a real partitioning scenario, only the latest task for a given partition key would be processed
    # Here we're simulating that by only considering the first task in the sorted list
    return sorted_tasks[0] if sorted_tasks else None

def check_tasks_processed(task_details):
    """Wait for tasks to be processed and return the processed task IDs."""
    print("\nChecking if tasks have been processed...")
    processed_tasks = set()
    
    for task_detail in task_details:
        task_id = task_detail["task_id"]
        sequence = task_detail["sequence"]
        
        # Try with retries
        for retry in range(3):  # More limited retries for this internal function
            status = get_task_status(task_id)
            
            if status and status.get("compute_statuses"):
                print(f"Task #{sequence} (ID: {task_id}) has been processed!")
                processed_tasks.add(task_id)
                break
            
            print(f"Task #{sequence} not yet processed. Waiting...")
            time.sleep(3)  # Wait between retries
    
    return processed_tasks

def main():
    """Main function to run the direct partitioning test."""
    parser = argparse.ArgumentParser(description="Test direct partitioning in TrueCost Orchestrator")
    parser.add_argument("--num-tasks", type=int, default=3, help="Number of tasks to create")
    parser.add_argument("--wait", type=float, default=2.0, help="Wait time between tasks in seconds")
    parser.add_argument("--scenario", default="direct-test-scenario", help="Scenario ID to use")
    parser.add_argument("--business", default="direct-test-business", help="Business type ID to use")
    parser.add_argument("--check-interval", type=float, default=3.0, help="Time between status checks")
    parser.add_argument("--max-checks", type=int, default=10, help="Maximum number of status checks")
    parser.add_argument("--wait-for-processing", type=int, default=10, help="Seconds to wait for processing after creation")
    
    args = parser.parse_args()
    
    print(f"Starting direct partitioning test with {args.num_tasks} tasks...")
    print(f"Using scenario_id={args.scenario}, business_type_id={args.business}")
    print(f"Wait time between tasks: {args.wait} seconds")
    print("=" * 60)
    
    # Create tasks
    task_details = []
    for i in range(1, args.num_tasks + 1):
        task_detail = create_task(args.scenario, args.business, i)
        if task_detail:
            task_details.append(task_detail)
        print(f"Waiting {args.wait} seconds before next task...")
        time.sleep(args.wait)
    
    if not task_details:
        print("No tasks could be created. Exiting.")
        sys.exit(1)
    
    print("\nAll tasks created. Simulating partitioning logic...")
    
    # Simulate partitioning to identify which task would be processed in a proper partitioning scenario
    latest_task = simulate_partitioning(task_details)
    print(f"\nAccording to partitioning logic, Task #{latest_task['sequence']} (ID: {latest_task['task_id']}) "
          f"should be the only one processed as it's the latest for this partition key.")
    
    # Wait for some time to allow processing to happen
    print(f"\nWaiting {args.wait_for_processing} seconds for tasks to be processed...")
    time.sleep(args.wait_for_processing)
    
    # Check if tasks have been processed
    processed_tasks = check_tasks_processed(task_details)
    
    # Monitor tasks for processing
    check_count = 0
    all_processed = False
    
    while check_count < args.max_checks and not all_processed:
        print(f"\nCheck #{check_count + 1} - Checking task statuses...")
        print("=" * 60)
        
        for task_detail in task_details:
            task_id = task_detail["task_id"]
            sequence = task_detail["sequence"]
            status = get_task_status(task_id)
            
            if status:
                print(f"Task #{sequence} (ID: {task_id})")
                print(f"Status: {status['status']}")
                
                # Check for compute_statuses and show detailed info
                if status.get("compute_statuses"):
                    print("  Compute statuses:")
                    for compute in status["compute_statuses"]:
                        print(f"    Scenario: {compute.get('scenario_id')}")
                        print(f"    Business Type: {compute.get('business_type_id')}")
                        print(f"    Status: {compute.get('status')}")
                    print("  TASK PROCESSED ✓")
                    processed_tasks.add(task_id)
                else:
                    print("  No compute statuses - PENDING/PROCESSING")
                print("-" * 40)
        
        # Show stats
        print(f"\nProcessed tasks: {len(processed_tasks)}/{len(task_details)}")
        if len(processed_tasks) > 0:
            print("Processed task IDs:")
            for task_id in processed_tasks:
                # Find the task detail to show the sequence number
                task_detail = next((t for t in task_details if t["task_id"] == task_id), None)
                if task_detail:
                    sequence = task_detail["sequence"]
                    print(f"  Task #{sequence}: {task_id}")
        
        # Check if we've seen enough tasks processed to make a determination
        if len(processed_tasks) > 0:
            # If latest task is processed, or if multiple tasks are processed, we can make a determination
            if latest_task["task_id"] in processed_tasks or len(processed_tasks) > 1:
                break
        
        check_count += 1
        if check_count < args.max_checks:
            print(f"\nWaiting {args.check_interval} seconds before next check...")
            time.sleep(args.check_interval)
    
    # Final analysis
    print("\nPartitioning Testing Results:")
    print("=" * 60)
    
    if len(processed_tasks) == 0:
        print("No tasks were processed during the monitoring period.")
        print("Cannot determine if partitioning is working.")
    elif len(processed_tasks) == 1:
        processed_task_id = list(processed_tasks)[0]
        processed_task = next((t for t in task_details if t["task_id"] == processed_task_id), None)
        
        if processed_task["task_id"] == latest_task["task_id"]:
            print("SUCCESS: Only the latest task was processed!")
            print(f"Task #{latest_task['sequence']} (ID: {latest_task['task_id']}) was correctly prioritized.")
            print("This simulates correct partitioning logic.")
        else:
            print(f"UNEXPECTED: Only task #{processed_task['sequence']} was processed, which is not the latest one.")
            print("This suggests that the partitioning logic wouldn't work as expected.")
    else:
        print(f"UNEXPECTED: Multiple tasks ({len(processed_tasks)}/{len(task_details)}) were processed.")
        print("In a proper partitioning scenario, only the latest task would be processed.")
        print("Processed tasks:")
        for task_id in processed_tasks:
            task = next((t for t in task_details if t["task_id"] == task_id), None)
            if task:
                print(f"  Task #{task['sequence']}: {task_id}")
    
    # Compare with expected behavior
    print("\nComparison with Expected Behavior:")
    print("=" * 60)
    
    if latest_task["task_id"] in processed_tasks:
        print("✓ The latest task was processed as expected.")
    else:
        print("✗ The latest task was NOT processed, indicating issues with task processing.")
    
    other_processed = [tid for tid in processed_tasks if tid != latest_task["task_id"]]
    if other_processed:
        print(f"✗ {len(other_processed)} other tasks were processed, which wouldn't happen with proper partitioning.")
    else:
        if len(processed_tasks) > 0:
            print("✓ No other tasks were processed, which is the expected behavior with partitioning.")

if __name__ == "__main__":
    main() 