import asyncio
import uvicorn
import logging
from fastapi import FastAPI
from app.api.router import router
from app.core.config import settings
from app.db.postgres import init_db
from app.services.eventhub import init_eventhub_consumer

app = FastAPI(title=settings.PROJECT_NAME)

app.include_router(router)

@app.on_event("startup")
async def startup_event():
    logging.info("Starting up application")
    # Initialize database
    await init_db()
    
    # Start EventHub consumer in the background using Confluent Kafka
    asyncio.create_task(init_eventhub_consumer())

@app.on_event("shutdown")
async def shutdown_event():
    logging.info("Shutting down application")
    # Cleanup connections if needed
    pass

if __name__ == "__main__":
    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=True) 