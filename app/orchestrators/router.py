"""
Main router for the orchestrator modules.
"""
from fastapi import APIRouter

from app.orchestrators.modules.revenue.api import router as revenue_router
from app.orchestrators.modules.rebates.api import router as rebates_router
from app.orchestrators.modules.specialty.api import router as specialty_router

# Create main router
router = APIRouter(prefix="/orchestrators")

# Include all module routers
router.include_router(revenue_router)
router.include_router(rebates_router)
router.include_router(specialty_router) 