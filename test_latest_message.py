#!/usr/bin/env python3
"""
Test script to verify that only the latest message for a specific partition key is processed.
This script sends two messages with the same scenario_id and business_type_id,
then checks if only the most recent one is processed.
"""
import asyncio
import json
import time
import uuid
import requests
import logging
from datetime import datetime, timezone

# Set up logging
logging.basicConfig(level=logging.INFO, 
                   format='%(asctime)s - %(levelname)s - %(message)s')

# Configuration
API_URL = "http://localhost:8080/tasks"
MAX_RETRIES = 3
RETRY_DELAY = 1
MAX_CHECKS = 20  # Number of status checks before giving up
CHECK_INTERVAL = 3  # Seconds between checks

def create_task(scenario_id, business_type_id, sequence_num):
    """Create a task with the specified scenario_id and business_type_id."""
    timestamp = datetime.now(timezone.utc).isoformat()
    
    payload = {
        "task_name": f"Latest Message Test {sequence_num}",
        "task_description": f"Testing latest message processing - sequence {sequence_num} - {timestamp}",
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
    
    logging.info(f"Creating task with scenario_id={scenario_id}, business_type_id={business_type_id}, sequence={sequence_num}")
    
    # Try with retries
    for retry in range(MAX_RETRIES):
        try:
            response = requests.post(API_URL, json=payload, timeout=10)
            response.raise_for_status()
            
            task_id = response.json().get("task_id")
            logging.info(f"Created task {task_id}")
            return {
                "task_id": task_id,
                "timestamp": timestamp,
                "sequence": sequence_num
            }
        except requests.exceptions.RequestException as e:
            logging.error(f"Attempt {retry+1}/{MAX_RETRIES} failed: {str(e)}")
            if retry < MAX_RETRIES - 1:
                logging.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logging.error("All retries failed")
                return None

def get_task_status(task_id):
    """Check the status of a task."""
    logging.info(f"Checking status for task {task_id}...")
    
    # Try with retries
    for retry in range(MAX_RETRIES):
        try:
            response = requests.get(f"{API_URL}/{task_id}", timeout=10)
            response.raise_for_status()
            
            status_data = response.json()
            return status_data
        except requests.exceptions.RequestException as e:
            logging.error(f"Attempt {retry+1}/{MAX_RETRIES} failed: {str(e)}")
            if retry < MAX_RETRIES - 1:
                logging.info(f"Retrying in {RETRY_DELAY} seconds...")
                time.sleep(RETRY_DELAY)
            else:
                logging.error("All retries failed")
                return None

async def test_latest_message_processing():
    """Main test function to verify latest message processing."""
    # Generate a unique test ID to avoid conflicting with other tests
    test_id = uuid.uuid4().hex[:8]
    scenario_id = f"scenario-{test_id}"
    business_type_id = f"business-{test_id}"
    
    logging.info(f"Starting latest message processing test with unique test ID: {test_id}")
    logging.info(f"Using scenario_id={scenario_id}, business_type_id={business_type_id}")
    logging.info("=" * 60)
    
    # Create first task
    task1 = create_task(scenario_id, business_type_id, 1)
    if not task1:
        logging.error("Failed to create first task. Exiting test.")
        return
    
    # Wait a bit before creating the second task
    wait_time = 3
    logging.info(f"Waiting {wait_time} seconds before sending second task...")
    time.sleep(wait_time)
    
    # Create second task with same scenario_id and business_type_id
    task2 = create_task(scenario_id, business_type_id, 2)
    if not task2:
        logging.error("Failed to create second task. Exiting test.")
        return
    
    # Wait for processing to begin
    logging.info(f"Tasks created. Waiting 10 seconds for processing to begin...")
    time.sleep(10)
    
    # Monitor processing
    tasks = [task1, task2]
    processed_tasks = set()
    check_count = 0
    
    while check_count < MAX_CHECKS and len(processed_tasks) < len(tasks):
        logging.info(f"Check #{check_count + 1} - Checking task statuses...")
        logging.info("=" * 60)
        
        for task in tasks:
            task_id = task["task_id"]
            sequence = task["sequence"]
            
            if task_id in processed_tasks:
                logging.info(f"Task #{sequence} (ID: {task_id}) was already processed.")
                continue
                
            status = get_task_status(task_id)
            
            if not status:
                logging.warning(f"Failed to get status for task #{sequence}")
                continue
                
            logging.info(f"Task #{sequence} (ID: {task_id}) - Status: {status['status']}")
            
            # Check if the task has been processed
            if status.get("compute_statuses"):
                logging.info(f"  Task #{sequence} has compute statuses - PROCESSED ✓")
                processed_tasks.add(task_id)
                
                # Log compute statuses
                for compute in status["compute_statuses"]:
                    logging.info(f"    Scenario: {compute.get('scenario_id')}")
                    logging.info(f"    Business Type: {compute.get('business_type_id')}")
                    logging.info(f"    Status: {compute.get('status')}")
            else:
                logging.info(f"  Task #{sequence} has no compute statuses - PENDING")
        
        # If we have processed tasks, we can make a determination
        if processed_tasks:
            break
            
        # Wait before next check
        if check_count < MAX_CHECKS - 1:
            logging.info(f"Waiting {CHECK_INTERVAL} seconds before next check...")
            time.sleep(CHECK_INTERVAL)
            
        check_count += 1
    
    # Analyze results
    logging.info("\nTest Results:")
    logging.info("=" * 60)
    
    if not processed_tasks:
        logging.info("No tasks were processed during the monitoring period.")
        logging.info("Cannot determine if the 'process only latest message' logic is working.")
        return
    
    # Check if only the latest task was processed
    if len(processed_tasks) == 1:
        processed_id = list(processed_tasks)[0]
        
        # Is it the latest task?
        if processed_id == task2["task_id"]:
            logging.info("SUCCESS: Only the latest task was processed!")
            logging.info(f"Task #{task2['sequence']} (ID: {task2['task_id']}) was correctly prioritized.")
            logging.info("The 'process only latest message' logic is working correctly.")
        else:
            logging.info("UNEXPECTED: Only the first task was processed instead of the latest one.")
            logging.info(f"Task #{task1['sequence']} (ID: {task1['task_id']}) was processed instead of task #{task2['sequence']}.")
            logging.info("The 'process only latest message' logic might not be working correctly.")
    else:
        logging.info(f"UNEXPECTED: Both tasks were processed ({len(processed_tasks)}/2).")
        logging.info("The 'process only latest message' logic should have prioritized only the latest task.")
        logging.info("Processed tasks:")
        for task_id in processed_tasks:
            task = next((t for t in tasks if t["task_id"] == task_id), None)
            if task:
                logging.info(f"  Task #{task['sequence']}: {task_id}")

if __name__ == "__main__":
    asyncio.run(test_latest_message_processing()) 