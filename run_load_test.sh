#!/bin/bash

# Script to run load tests with different configurations

# Make sure the required dependencies are installed
echo "Checking dependencies..."
pip install httpx asyncio

# Default API URL
API_URL="http://localhost:8000/api/orchestrate"

function run_test() {
    local concurrency=$1
    local requests=$2
    local check_tasks=$3
    
    echo "=========================================="
    echo "Running load test with:"
    echo "- Concurrency: $concurrency"
    echo "- Total Requests: $requests"
    echo "- Check Tasks: $check_tasks"
    echo "=========================================="
    
    local check_tasks_flag=""
    if [ "$check_tasks" = "true" ]; then
        check_tasks_flag="--check-tasks"
    fi
    
    python load_test.py --url "$API_URL" --concurrency "$concurrency" --requests "$requests" $check_tasks_flag
    
    echo "Test completed. Press Enter to continue..."
    read
}

# Make the load_test.py script executable
chmod +x load_test.py

# Main menu
while true; do
    clear
    echo "===== ORCHESTRATOR LOAD TEST MENU ====="
    echo "1. Quick test (100 requests, 10 concurrent)"
    echo "2. Medium test (500 requests, 50 concurrent)"
    echo "3. Full load test (1000 requests, 100 concurrent)"
    echo "4. High concurrency test (1000 requests, 200 concurrent)"
    echo "5. Extreme test (10000 requests, 500 concurrent)"
    echo "6. Custom test"
    echo "7. Exit"
    echo ""
    echo -n "Select an option (1-7): "
    read option
    
    case $option in
        1)
            run_test 10 100 true
            ;;
        2)
            run_test 50 500 true
            ;;
        3)
            run_test 100 1000 false
            ;;
        4)
            run_test 200 1000 false
            ;;
        5)
            run_test 500 10000 false
            ;;
        6)
            echo -n "Enter concurrency level: "
            read custom_concurrency
            echo -n "Enter number of requests: "
            read custom_requests
            echo -n "Check task statuses after test? (y/n): "
            read check_tasks_response
            
            check_tasks="false"
            if [[ "$check_tasks_response" == "y" || "$check_tasks_response" == "Y" ]]; then
                check_tasks="true"
            fi
            
            run_test "$custom_concurrency" "$custom_requests" "$check_tasks"
            ;;
        7)
            echo "Exiting..."
            exit 0
            ;;
        *)
            echo "Invalid option. Press Enter to continue..."
            read
            ;;
    esac
done 