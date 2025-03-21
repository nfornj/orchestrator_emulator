import asyncio
import random
import logging
from app.core.config import settings
from app.services.storage import get_payload_from_redis, store_result_in_postgres, set_task_status

async def mock_api_call(name, min_delay, max_delay, data):
    delay = random.randint(min_delay, max_delay) / 1000.0  # Convert to seconds
    logging.info(f"Making mock {name} API call with delay {delay} seconds")
    await asyncio.sleep(delay)
    
    # Simulate response data
    return {
        "service": name,
        "input_data": data,
        "processed": True,
        "delay_ms": delay * 1000
    }

async def process_task(task_id, scenario_id, business_type_id):
    # Update status to processing
    print(f"PROCESSOR: Starting process_task for {task_id}")
    await set_task_status(task_id, "processing")
    
    try:
        # Get the full payload from Redis
        print(f"PROCESSOR: Getting payload from Redis for {task_id}")
        payload = await get_payload_from_redis(task_id)
        if not payload:
            print(f"PROCESSOR: Payload not found in Redis for task_id {task_id}")
            logging.error(f"Payload not found in Redis for task_id {task_id}")
            await store_result_in_postgres(
                task_id, scenario_id, business_type_id, 
                {"error": "Payload not found"}, "failed"
            )
            return
        
        print(f"PROCESSOR: Found payload in Redis for {task_id}")
        
        # Find the matching compute item
        compute_item = None
        for compute in payload['compute']:
            if compute['scenario_id'] == scenario_id and compute['business_type_id'] == business_type_id:
                compute_item = compute
                break
        
        if not compute_item:
            print(f"PROCESSOR: Compute item not found for scenario_id {scenario_id} and business_type_id {business_type_id}")
            logging.error(f"Compute item not found for scenario_id {scenario_id} and business_type_id {business_type_id}")
            await store_result_in_postgres(
                task_id, scenario_id, business_type_id, 
                {"error": "Compute item not found"}, "failed"
            )
            return
        
        print(f"PROCESSOR: Found compute item for {task_id}, starting API calls")
        
        # Make the mock API calls in parallel
        revenue_task = mock_api_call(
            "revenue", 
            settings.REVENUE_DELAY_MIN, 
            settings.REVENUE_DELAY_MAX, 
            compute_item['revenue']
        )
        
        rebate_task = mock_api_call(
            "rebate", 
            settings.REBATE_DELAY_MIN, 
            settings.REBATE_DELAY_MAX, 
            compute_item['rebate']
        )
        
        speciality_task = mock_api_call(
            "speciality", 
            settings.SPECIALTY_DELAY_MIN, 
            settings.SPECIALTY_DELAY_MAX, 
            compute_item['speciality']
        )
        
        # Await all tasks to complete
        revenue_result, rebate_result, speciality_result = await asyncio.gather(
            revenue_task, rebate_task, speciality_task
        )
        
        # Combine results
        result = {
            "task_id": task_id,
            "scenario_id": scenario_id,
            "business_type_id": business_type_id,
            "revenue": revenue_result,
            "rebate": rebate_result,
            "speciality": speciality_result
        }
        
        # Store the result in PostgreSQL
        print(f"PROCESSOR: Storing result in PostgreSQL for {task_id}")
        await store_result_in_postgres(
            task_id, scenario_id, business_type_id, result, "completed"
        )
        
        print(f"PROCESSOR: Task {task_id} for scenario {scenario_id} and business type {business_type_id} completed")
        logging.info(f"Task {task_id} for scenario {scenario_id} and business type {business_type_id} completed")
        
    except Exception as e:
        print(f"PROCESSOR: Error processing task {task_id}: {str(e)}")
        logging.exception(f"Error processing task {task_id}: {str(e)}")
        # Store error in PostgreSQL
        await store_result_in_postgres(
            task_id, scenario_id, business_type_id, 
            {"error": str(e)}, "failed"
        ) 