import json
import redis.asyncio as redis
from app.core.config import settings

redis_pool = None

async def get_redis_pool():
    global redis_pool
    if redis_pool is None:
        redis_pool = redis.ConnectionPool(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            decode_responses=True
        )
    return redis_pool

async def close_redis_pool():
    global redis_pool
    if redis_pool is not None:
        redis_pool = None

async def set_json(key: str, value: dict, ttl: int = None):
    pool = await get_redis_pool()
    client = redis.Redis(connection_pool=pool)
    serialized = json.dumps(value)
    try:
        if ttl:
            await client.setex(key, ttl, serialized)
        else:
            await client.set(key, serialized)
    finally:
        await client.close()

async def get_json(key: str):
    pool = await get_redis_pool()
    client = redis.Redis(connection_pool=pool)
    try:
        data = await client.get(key)
        if data:
            return json.loads(data)
        return None
    finally:
        await client.close()

async def set_task_status(task_id: str, status: str, ttl: int = None):
    if ttl is None:
        if status == "completed":
            ttl = settings.REDIS_COMPLETED_TTL
        else:
            ttl = settings.REDIS_STATUS_TTL
    
    await set_json(f"status:{task_id}", {"task_id": task_id, "status": status}, ttl) 