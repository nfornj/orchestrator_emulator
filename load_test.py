#!/usr/bin/env python3
import asyncio
import httpx
import time
import uuid
import json
import argparse
import statistics
from datetime import datetime
from typing import List, Dict, Any, Optional

# Configure the default settings
DEFAULT_API_URL = "http://localhost:8000/api/orchestrate"
DEFAULT_TOTAL_REQUESTS = 1000
DEFAULT_CONCURRENCY = 100
DEFAULT_TIMEOUT = 30  # seconds

class LoadTestResults:
    """Store and analyze load test results"""
    
    def __init__(self):
        self.response_times = []
        self.status_codes = {}
        self.successful_requests = 0
        self.failed_requests = 0
        self.start_time = None
        self.end_time = None
        self.errors = []
        self.task_ids = []
    
    def start(self):
        """Mark the start of the test"""
        self.start_time = time.time()
    
    def end(self):
        """Mark the end of the test"""
        self.end_time = time.time()
    
    def add_result(self, response_time: float, status_code: int, success: bool, task_id: Optional[str] = None, error: Optional[str] = None):
        """Add a request result"""
        self.response_times.append(response_time)
        
        # Count status codes
        if status_code in self.status_codes:
            self.status_codes[status_code] += 1
        else:
            self.status_codes[status_code] = 1
        
        # Track success/failure
        if success:
            self.successful_requests += 1
            if task_id:
                self.task_ids.append(task_id)
        else:
            self.failed_requests += 1
            if error:
                self.errors.append(error)
    
    def print_summary(self):
        """Print a summary of the test results"""
        total_time = self.end_time - self.start_time if self.end_time and self.start_time else 0
        total_requests = self.successful_requests + self.failed_requests
        
        print("\n===== LOAD TEST SUMMARY =====")
        print(f"Total requests: {total_requests}")
        print(f"Successful requests: {self.successful_requests}")
        print(f"Failed requests: {self.failed_requests}")
        print(f"Success rate: {(self.successful_requests / total_requests * 100):.2f}%")
        print(f"Total test time: {total_time:.2f} seconds")
        print(f"Requests per second: {total_requests / total_time:.2f}")
        
        if self.response_times:
            print("\n===== RESPONSE TIME STATS =====")
            print(f"Min response time: {min(self.response_times):.4f} seconds")
            print(f"Max response time: {max(self.response_times):.4f} seconds")
            print(f"Avg response time: {sum(self.response_times) / len(self.response_times):.4f} seconds")
            print(f"Median response time: {statistics.median(self.response_times):.4f} seconds")
            
            if len(self.response_times) > 1:
                print(f"Std dev response time: {statistics.stdev(self.response_times):.4f} seconds")
            
            # Calculate percentiles
            sorted_times = sorted(self.response_times)
            p50_idx = int(len(sorted_times) * 0.5)
            p90_idx = int(len(sorted_times) * 0.9)
            p95_idx = int(len(sorted_times) * 0.95)
            p99_idx = int(len(sorted_times) * 0.99)
            
            print(f"50th percentile (p50): {sorted_times[p50_idx]:.4f} seconds")
            print(f"90th percentile (p90): {sorted_times[p90_idx]:.4f} seconds")
            print(f"95th percentile (p95): {sorted_times[p95_idx]:.4f} seconds")
            print(f"99th percentile (p99): {sorted_times[p99_idx]:.4f} seconds")
        
        print("\n===== STATUS CODE DISTRIBUTION =====")
        for status_code, count in sorted(self.status_codes.items()):
            print(f"Status {status_code}: {count} ({count / total_requests * 100:.2f}%)")
        
        if self.errors:
            print("\n===== SAMPLE ERRORS =====")
            # Show up to 5 unique errors
            unique_errors = set(self.errors[:20])
            for i, error in enumerate(list(unique_errors)[:5]):
                print(f"Error {i+1}: {error}")
            
            if len(unique_errors) > 5:
                print(f"... and {len(unique_errors) - 5} more unique error types")
                
        print("\n===== GENERATED TASK IDs =====")
        print(f"Total tasks created: {len(self.task_ids)}")
        if self.task_ids:
            print("Sample task IDs (first 5):")
            for i, task_id in enumerate(self.task_ids[:5]):
                print(f"  {i+1}. {task_id}")

async def send_request(
    client: httpx.AsyncClient,
    url: str,
    payload: Dict[str, Any],
    results: LoadTestResults,
    request_id: int
) -> None:
    """Send a single request and record the results"""
    start_time = time.time()
    success = False
    status_code = 0
    task_id = None
    error_msg = None
    
    try:
        response = await client.post(url, json=payload, timeout=DEFAULT_TIMEOUT)
        status_code = response.status_code
        end_time = time.time()
        response_time = end_time - start_time
        
        if response.status_code == 200:
            success = True
            try:
                response_data = response.json()
                task_id = response_data.get("task_id")
            except:
                pass
        else:
            try:
                error_msg = response.text
            except:
                error_msg = f"HTTP error {response.status_code}"
                
    except Exception as e:
        end_time = time.time()
        response_time = end_time - start_time
        error_msg = str(e)
    
    # Record the result
    results.add_result(
        response_time=response_time,
        status_code=status_code,
        success=success,
        task_id=task_id,
        error=error_msg
    )
    
    if request_id % 100 == 0:
        print(f"Processed {request_id} requests...")

def generate_payload(request_id: int) -> Dict[str, Any]:
    """Generate a random payload for the orchestration request"""
    scenario_id = str(uuid.uuid4())
    business_type_id = str(uuid.uuid4())
    
    return {
        "task_name": f"Load Test {request_id}",
        "task_description": f"Performance testing request #{request_id} generated at {datetime.now().isoformat()}",
        "payload": [
            {
                "revenue": {
                    "scenario_id": scenario_id,
                    "business_type_id": business_type_id
                },
                "rebates": None,
                "specialty": None
            }
        ]
    }

async def run_load_test(
    url: str,
    total_requests: int,
    concurrency: int
) -> LoadTestResults:
    """Run a load test with the specified parameters"""
    results = LoadTestResults()
    results.start()
    
    # Create a semaphore to limit concurrency
    semaphore = asyncio.Semaphore(concurrency)
    
    async def bounded_send_request(request_id: int):
        async with semaphore:
            payload = generate_payload(request_id)
            async with httpx.AsyncClient() as client:
                await send_request(client, url, payload, results, request_id)
    
    # Create tasks for all requests
    tasks = []
    for i in range(1, total_requests + 1):
        tasks.append(asyncio.create_task(bounded_send_request(i)))
    
    # Wait for all tasks to complete
    await asyncio.gather(*tasks)
    
    results.end()
    return results

async def check_task_statuses(task_ids: List[str], base_url: str):
    """Check the status of completed tasks"""
    print("\n===== CHECKING TASK STATUSES =====")
    print(f"Checking status for {len(task_ids)} tasks...")
    
    status_counts = {}
    api_url = base_url.replace("/orchestrate", "")
    
    async with httpx.AsyncClient() as client:
        for i, task_id in enumerate(task_ids[:10]):  # Check first 10 tasks
            try:
                response = await client.get(f"{api_url}/tasks/{task_id}")
                if response.status_code == 200:
                    task_data = response.json()
                    status = task_data.get("status", "UNKNOWN")
                    
                    if status in status_counts:
                        status_counts[status] += 1
                    else:
                        status_counts[status] = 1
                        
                    print(f"Task {i+1}: {task_id} - Status: {status}")
            except Exception as e:
                print(f"Error checking task {task_id}: {str(e)}")
    
    print("\nTask status distribution:")
    for status, count in status_counts.items():
        print(f"  {status}: {count}")

def parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description="Load test for Orchestrator API")
    parser.add_argument("--url", type=str, default=DEFAULT_API_URL,
                        help=f"URL of the orchestrator API (default: {DEFAULT_API_URL})")
    parser.add_argument("--requests", type=int, default=DEFAULT_TOTAL_REQUESTS,
                        help=f"Total number of requests to send (default: {DEFAULT_TOTAL_REQUESTS})")
    parser.add_argument("--concurrency", type=int, default=DEFAULT_CONCURRENCY,
                        help=f"Maximum number of concurrent requests (default: {DEFAULT_CONCURRENCY})")
    parser.add_argument("--check-tasks", action="store_true",
                        help="Check status of tasks after test (default: False)")
    return parser.parse_args()

async def main():
    args = parse_arguments()
    
    print(f"Starting load test with {args.requests} total requests and {args.concurrency} concurrency level")
    print(f"Target URL: {args.url}")
    
    results = await run_load_test(args.url, args.requests, args.concurrency)
    results.print_summary()
    
    if args.check_tasks and results.task_ids:
        await check_task_statuses(results.task_ids, args.url)

if __name__ == "__main__":
    asyncio.run(main()) 