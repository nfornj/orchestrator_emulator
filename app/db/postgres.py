import asyncpg
from app.core.config import settings

db_pool = None

async def get_db_pool():
    global db_pool
    if db_pool is None:
        db_pool = await asyncpg.create_pool(
            user=settings.POSTGRES_USER,
            password=settings.POSTGRES_PASSWORD,
            host=settings.POSTGRES_HOST,
            port=settings.POSTGRES_PORT,
            database=settings.POSTGRES_DB
        )
    return db_pool

async def close_db_pool():
    global db_pool
    if db_pool:
        await db_pool.close()
        db_pool = None

async def init_db():
    print("DEBUG: Initializing database - starting table creation")
    try:
        pool = await get_db_pool()
        print("DEBUG: Got PostgreSQL connection pool for init_db")
        async with pool.acquire() as conn:
            print("DEBUG: Acquired connection from pool for init_db")
            # Create task results table
            await conn.execute('''
            CREATE TABLE IF NOT EXISTS task_results (
                id SERIAL PRIMARY KEY,
                task_id TEXT NOT NULL,
                scenario_id TEXT NOT NULL,
                business_type_id TEXT NOT NULL,
                result_data JSONB NOT NULL,
                status TEXT NOT NULL,
                created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (task_id, scenario_id, business_type_id)
            );
            
            CREATE INDEX IF NOT EXISTS idx_task_results_task_id ON task_results(task_id);
            CREATE INDEX IF NOT EXISTS idx_task_results_scenario_business ON task_results(scenario_id, business_type_id);
            ''')
            print("DEBUG: Database initialization complete - tables created successfully")
    except Exception as e:
        print(f"ERROR: Exception in init_db: {str(e)}")
        import traceback
        print(f"ERROR TRACEBACK: {traceback.format_exc()}")
        # This is a critical error, we should re-raise it
        raise 