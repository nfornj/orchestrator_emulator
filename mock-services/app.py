import asyncio
import json
import logging
import os
import uuid
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
import uvicorn

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

# Create the FastAPI app
app = FastAPI(
    title="Mock Services",
    description="Mock services for revenue, rebates, and specialty calculations",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    """
    return {"status": "healthy"}


@app.post("/revenue")
async def revenue_calculation(request: Request):
    """
    Mock revenue calculation endpoint.
    """
    try:
        payload = await request.json()
        logger.info(f"Received revenue calculation request with {len(payload)} items")
        
        # Simulate processing time
        await asyncio.sleep(1)
        
        # Process each item
        results = []
        for item in payload:
            # Validate required fields
            if "scenario_id" not in item or "business_type_id" not in item:
                raise HTTPException(status_code=400, detail="Missing required fields")
            
            # Generate a mock result
            result = {
                "scenario_id": item["scenario_id"],
                "business_type_id": item["business_type_id"],
                "revenue_result": f"Revenue-{uuid.uuid4()}",
                "amount": float(f"{(uuid.uuid4().int % 10000) / 100:.2f}"),  # Random amount
            }
            results.append(result)
        
        return {
            "status": "success",
            "data": results,
        }
    
    except Exception as e:
        logger.error(f"Error in revenue calculation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/rebates")
async def rebates_calculation(request: Request):
    """
    Mock rebates calculation endpoint.
    """
    try:
        payload = await request.json()
        logger.info(f"Received rebates calculation request with {len(payload)} items")
        
        # Simulate processing time
        await asyncio.sleep(1.5)
        
        # Process each item
        results = []
        for item in payload:
            # Validate required fields
            if "scenario_id" not in item or "business_type_id" not in item:
                raise HTTPException(status_code=400, detail="Missing required fields")
            
            # Generate a mock result
            result = {
                "scenario_id": item["scenario_id"],
                "business_type_id": item["business_type_id"],
                "rebate_result": f"Rebate-{uuid.uuid4()}",
                "amount": float(f"{(uuid.uuid4().int % 5000) / 100:.2f}"),  # Random amount
            }
            results.append(result)
        
        return {
            "status": "success",
            "data": results,
        }
    
    except Exception as e:
        logger.error(f"Error in rebates calculation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@app.post("/specialty")
async def specialty_calculation(request: Request):
    """
    Mock specialty calculation endpoint.
    """
    try:
        payload = await request.json()
        logger.info(f"Received specialty calculation request with {len(payload)} items")
        
        # Simulate processing time
        await asyncio.sleep(2)
        
        # Process each item
        results = []
        for item in payload:
            # Validate required fields
            if "scenario_id" not in item or "business_type_id" not in item:
                raise HTTPException(status_code=400, detail="Missing required fields")
            
            # Generate a mock result
            result = {
                "scenario_id": item["scenario_id"],
                "business_type_id": item["business_type_id"],
                "specialty_result": f"Specialty-{uuid.uuid4()}",
                "amount": float(f"{(uuid.uuid4().int % 7500) / 100:.2f}"),  # Random amount
            }
            results.append(result)
        
        return {
            "status": "success",
            "data": results,
        }
    
    except Exception as e:
        logger.error(f"Error in specialty calculation: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv("PORT", 8001))
    
    # Run the application with uvicorn
    uvicorn.run(
        "app:app",
        host="0.0.0.0",
        port=port,
        reload=bool(os.getenv("DEBUG", "False").lower() == "true"),
    ) 