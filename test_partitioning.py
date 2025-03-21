#!/usr/bin/env python3
"""
Test script to verify Kafka partitioning in TrueCost Orchestrator.
This script sends multiple tasks with the same scenario_id and business_type_id,
then checks their status to see if they're being processed correctly.
"""
import argparse
import json
import time
import uuid
import requests
from pprint import pprint

# Configuration
API_URL = "http://localhost:8080/tasks"

def create_task(scenario_id, business_type_id, sequence_num):
    """Create a task with the specified scenario_id and business_type_id."""
    payload = {
        "task_name": f"Partition Test {sequence_num}",
        "task_description": f"Testing partitioning - sequence {sequence_num} - {time.time()}",
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
    response = requests.post(API_URL, json=payload)
    
    if response.status_code == 200:
        task_id = response.json().get("task_id")
        print(f"Created task {task_id}")
        return task_id
    else:
        print(f"Failed to create task: {response.status_code} - {response.text}")
        return None

def get_task_status(task_id):
    """Check the status of a task."""
    response = requests.get(f"{API_URL}/{task_id}")
    
    if response.status_code == 200:
        return response.json()
    else:
        print(f"Failed to get task status: {response.status_code} - {response.text}")
        return None

def main():
    """Main function to run the partition test."""
    parser = argparse.ArgumentParser(description="Test Kafka partitioning in TrueCost Orchestrator")
    parser.add_argument("--num-tasks", type=int, default=5, help="Number of tasks to create")
    parser.add_argument("--wait", type=float, default=2.0, help="Wait time between tasks in seconds")
    parser.add_argument("--scenario", default="test-partition-scenario-2", help="Scenario ID to use")
    parser.add_argument("--business", default="test-partition-business-2", help="Business type ID to use")
    parser.add_argument("--check-interval", type=float, default=2.0, help="Time between status checks")
    parser.add_argument("--max-checks", type=int, default=5, help="Maximum number of status checks")
    
    args = parser.parse_args()
    
    print(f"Starting partition test with {args.num_tasks} tasks...")
    print(f"Using scenario_id={args.scenario}, business_type_id={args.business}")
    print(f"Wait time between tasks: {args.wait} seconds")
    print("=" * 60)
    
    # Create tasks
    task_ids = []
    for i in range(1, args.num_tasks + 1):
        task_id = create_task(args.scenario, args.business, i)
        if task_id:
            task_ids.append(task_id)
        print(f"Waiting {args.wait} seconds before next task...")
        time.sleep(args.wait)
    
    print("\nAll tasks created. Monitoring processing status...")
    
    # Monitor tasks for processing
    check_count = 0
    all_processed = False
    processed_tasks = set()
    
    while check_count < args.max_checks and not all_processed:
        print(f"\nCheck #{check_count + 1} - Checking task statuses...")
        print("=" * 60)
        
        for task_id in task_ids:
            status = get_task_status(task_id)
            if status:
                print(f"Task ID: {task_id}")
                print(f"Status: {status['status']}")
                
                if status.get("compute_statuses"):
                    print("  Compute statuses found - PROCESSED ✓")
                    processed_tasks.add(task_id)
                else:
                    print("  No compute statuses - PENDING")
                print("-" * 40)
        
        # Check if all tasks are processed
        if len(processed_tasks) == len(task_ids):
            all_processed = True
            break
        
        # Show stats
        print(f"\nProcessed tasks: {len(processed_tasks)}/{len(task_ids)}")
        if len(processed_tasks) > 0:
            print("Processed task IDs:")
            for task_id in processed_tasks:
                # Show which number in the sequence this task is
                task_index = task_ids.index(task_id)
                print(f"  Task #{task_index + 1}: {task_id}")
        
        if not all_processed:
            check_count += 1
            if check_count < args.max_checks:
                print(f"\nWaiting {args.check_interval} seconds before next check...")
                time.sleep(args.check_interval)
    
    # Final analysis
    print("\nPartition Testing Results:")
    print("=" * 60)
    
    if len(processed_tasks) == 0:
        print("No tasks were processed during the monitoring period.")
    elif len(processed_tasks) == 1:
        # Check if the processed task is the last one
        processed_task_id = list(processed_tasks)[0]
        processed_index = task_ids.index(processed_task_id)
        
        if processed_index == len(task_ids) - 1:
            print("SUCCESS: Only the latest task was processed!")
            print(f"Task #{len(task_ids)} (ID: {processed_task_id}) was correctly prioritized.")
            print("The partitioning logic is working as expected.")
        else:
            print(f"UNEXPECTED: Only task #{processed_index + 1} was processed, which is not the latest one.")
            print("This suggests that the partitioning logic might not be working as expected.")
    else:
        print(f"UNEXPECTED: Multiple tasks ({len(processed_tasks)}/{len(task_ids)}) were processed.")
        print("The partitioning logic should prioritize only the latest task for a given partition key.")
        print("Processed tasks:")
        for task_id in processed_tasks:
            task_index = task_ids.index(task_id)
            print(f"  Task #{task_index + 1}: {task_id}")

if __name__ == "__main__":
    main() 