import os
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from contextlib import asynccontextmanager

# Get the database URL from environment variable
DATABASE_URL = os.getenv(
    "DATABASE_URL", "postgresql://postgres:postgres@postgres:5432/orchestrator"
)

# Create a synchronous engine for alembic migrations
# Convert to async format for sqlalchemy
sync_engine = create_engine(DATABASE_URL)

# Create async engine for the application
async_engine = create_async_engine(DATABASE_URL.replace("postgresql://", "postgresql+asyncpg://"))

# SessionLocal factory
AsyncSessionLocal = sessionmaker(
    bind=async_engine, class_=AsyncSession, expire_on_commit=False
)

# Create a base class for models
Base = declarative_base()

@asynccontextmanager
async def get_db():
    """
    Async context manager for database sessions.
    
    Example:
        async with get_db() as db:
            # do something with db
    """
    db = AsyncSessionLocal()
    try:
        yield db
    finally:
        await db.close()

# This is the function to use with FastAPI Depends
async def get_db_dependency():
    """
    Dependency to get a database session for FastAPI endpoints.
    
    Example:
        @app.get("/items/")
        async def get_items(db: AsyncSession = Depends(get_db_dependency)):
            # do something with db
    """
    async with AsyncSessionLocal() as db:
        yield db 