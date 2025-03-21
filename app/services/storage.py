import json
from app.db.redis import set_json, get_json, set_task_status
from app.db.postgres import get_db_pool
from app.core.config import settings

async def store_payload_in_redis(task_id: str, payload):
    # Store the entire payload in Redis with expiry
    payload_dict = payload.model_dump()
    await set_json(f"payload:{task_id}", payload_dict, settings.REDIS_PAYLOAD_TTL)
    
    # Set initial status to pending
    await set_task_status(task_id, "pending")

async def get_payload_from_redis(task_id: str):
    print(f"STORAGE: Getting payload from Redis for task_id {task_id}")
    key = f"payload:{task_id}"
    print(f"STORAGE: Redis key is {key}")
    result = await get_json(key)
    if result:
        print(f"STORAGE: Successfully retrieved payload for {task_id} from Redis")
    else:
        print(f"STORAGE: Failed to retrieve payload for {task_id} from Redis, got None")
    return result

async def store_result_in_postgres(task_id: str, scenario_id: str, business_type_id: str, result_data, status: str):
    print(f"DEBUG: Storing result in PostgreSQL for task_id {task_id}, scenario_id {scenario_id}, business_type_id {business_type_id}")
    try:
        pool = await get_db_pool()
        print(f"DEBUG: Got PostgreSQL connection pool for storing result")
        async with pool.acquire() as conn:
            print(f"DEBUG: Acquired connection from pool for storing result")
            await conn.execute('''
            INSERT INTO task_results (task_id, scenario_id, business_type_id, result_data, status)
            VALUES ($1, $2, $3, $4, $5)
            ON CONFLICT (task_id, scenario_id, business_type_id) 
            DO UPDATE SET result_data = $4, status = $5, updated_at = CURRENT_TIMESTAMP
            ''', task_id, scenario_id, business_type_id, json.dumps(result_data), status)
            print(f"DEBUG: Successfully stored result in PostgreSQL for {task_id}")
    except Exception as e:
        print(f"ERROR: Exception in store_result_in_postgres for {task_id}: {str(e)}")
        import traceback
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        # Continue execution despite error

async def get_task_status(task_id: str):
    print(f"DEBUG: Getting task status for {task_id}")
    # First check Redis for status
    status_data = await get_json(f"status:{task_id}")
    
    if status_data:
        print(f"DEBUG: Found task status in Redis for {task_id}: {status_data}")
        # Make sure the task_id is included in the response
        status_data['task_id'] = task_id
        return status_data
    
    print(f"DEBUG: Task status not found in Redis for {task_id}, checking PostgreSQL")
    # If not in Redis, check PostgreSQL
    try:
        pool = await get_db_pool()
        print(f"DEBUG: Got PostgreSQL connection pool")
        async with pool.acquire() as conn:
            print(f"DEBUG: Acquired connection from pool")
            results = await conn.fetch('''
            SELECT scenario_id, business_type_id, status, result_data
            FROM task_results
            WHERE task_id = $1
            ''', task_id)
            
            print(f"DEBUG: PostgreSQL query executed, found {len(results) if results else 0} results")
            
            if not results:
                print(f"DEBUG: No results found in PostgreSQL for task_id {task_id}")
                return None
            
            # Compute aggregate status
            statuses = [row['status'] for row in results]
            if all(status == 'completed' for status in statuses):
                overall_status = 'completed'
            elif any(status == 'processing' for status in statuses):
                overall_status = 'processing'
            elif any(status == 'failed' for status in statuses):
                overall_status = 'failed'
            else:
                overall_status = 'pending'
            
            compute_statuses = [
                {
                    'scenario_id': row['scenario_id'],
                    'business_type_id': row['business_type_id'],
                    'status': row['status'],
                    'result': json.loads(row['result_data']) if row['result_data'] else None
                }
                for row in results
            ]
            
            status_data = {
                'task_id': task_id,
                'status': overall_status,
                'compute_statuses': compute_statuses
            }
            
            print(f"DEBUG: Updating Redis with status data: {status_data}")
            # Update Redis with the status
            await set_task_status(task_id, overall_status)
            
            return status_data
    except Exception as e:
        print(f"ERROR: Exception in get_task_status for {task_id}: {str(e)}")
        import traceback
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        # Return a basic status without crashing
        return {"task_id": task_id, "status": "processing", "compute_statuses": None} 