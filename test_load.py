#!/usr/bin/env python3
"""
Load testing script for the TrueCost Orchestrator API.
This script sends multiple requests to create tasks, which will generate Kafka messages.
"""
import argparse
import json
import random
import time
import uuid
from concurrent.futures import ThreadPoolExecutor

import requests

# Configuration
DEFAULT_URL = "http://localhost:8080/tasks"
DEFAULT_REQUESTS = 100
DEFAULT_CONCURRENCY = 5
DEFAULT_DELAY = 0.1  # seconds between requests


def generate_payload():
    """Generate a random task payload."""
    scenario_id = f"scenario-{random.randint(1, 10)}"
    business_type_id = f"business-{random.randint(1, 5)}"
    
    # Revenue between $10,000 and $1,000,000
    revenue_value = random.randint(10000, 1000000)
    
    # Rebate between 5% and 20% of revenue
    rebate_percentage = random.randint(5, 20)
    rebate_value = int(revenue_value * (rebate_percentage / 100))
    
    # Speciality types
    speciality_type = random.choice(["Cardiology", "Oncology", "Neurology", "Primary Care"])
    region = f"region-{random.randint(1, 5)}"
    
    return {
        "task_name": f"Load Test Task {uuid.uuid4().hex[:8]}",
        "task_description": f"Automatically generated task for load testing - {time.time()}",
        "app_id": random.randint(100, 999),
        "compute": [
            {
                "scenario_id": scenario_id,
                "business_type_id": business_type_id,
                "revenue": {
                    "value": revenue_value,
                    "currency": "USD"
                },
                "rebate": {
                    "value": rebate_value,
                    "percentage": rebate_percentage
                },
                "speciality": {
                    "type": speciality_type,
                    "region": region
                }
            }
        ]
    }


def send_request(url, request_id):
    """Send a single request and return the result."""
    try:
        payload = generate_payload()
        headers = {"Content-Type": "application/json"}
        
        print(f"Request {request_id}: Sending task creation request...")
        response = requests.post(url, json=payload, headers=headers)
        
        if response.status_code == 200:
            task_id = response.json().get("task_id")
            print(f"Request {request_id}: Task created with ID: {task_id}")
            return {"success": True, "task_id": task_id}
        else:
            print(f"Request {request_id}: Failed with status {response.status_code}")
            return {"success": False, "status_code": response.status_code, "response": response.text}
    
    except Exception as e:
        print(f"Request {request_id}: Error - {str(e)}")
        return {"success": False, "error": str(e)}


def main():
    """Main function to parse arguments and run the load test."""
    parser = argparse.ArgumentParser(description="Load testing script for TrueCost Orchestrator API")
    parser.add_argument("--url", default=DEFAULT_URL, help=f"API endpoint URL (default: {DEFAULT_URL})")
    parser.add_argument("--requests", type=int, default=DEFAULT_REQUESTS, 
                        help=f"Number of requests to send (default: {DEFAULT_REQUESTS})")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                        help=f"Number of concurrent requests (default: {DEFAULT_CONCURRENCY})")
    parser.add_argument("--delay", type=float, default=DEFAULT_DELAY,
                        help=f"Delay between requests in seconds (default: {DEFAULT_DELAY})")
    
    args = parser.parse_args()
    
    print(f"Starting load test with {args.requests} requests...")
    print(f"URL: {args.url}")
    print(f"Concurrency: {args.concurrency}")
    print(f"Delay between requests: {args.delay} seconds")
    print("-" * 50)
    
    results = {"success": 0, "failed": 0, "task_ids": []}
    start_time = time.time()
    
    # Using ThreadPoolExecutor for concurrent requests
    with ThreadPoolExecutor(max_workers=args.concurrency) as executor:
        futures = []
        
        for i in range(1, args.requests + 1):
            futures.append(executor.submit(send_request, args.url, i))
            time.sleep(args.delay)  # Add delay between requests
        
        for future in futures:
            result = future.result()
            if result.get("success"):
                results["success"] += 1
                results["task_ids"].append(result.get("task_id"))
            else:
                results["failed"] += 1
    
    end_time = time.time()
    duration = end_time - start_time
    
    # Print summary
    print("\n" + "=" * 50)
    print("Load Test Summary:")
    print(f"Total Requests: {args.requests}")
    print(f"Successful: {results['success']}")
    print(f"Failed: {results['failed']}")
    print(f"Duration: {duration:.2f} seconds")
    print(f"Requests/second: {args.requests / duration:.2f}")
    print("=" * 50)
    print("\nCheck the RedPanda Console (http://localhost:8085) to view the Kafka messages generated by these tasks.")


if __name__ == "__main__":
    main() 