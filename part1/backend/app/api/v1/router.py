"""
API v1 Router registry.
"""

from fastapi import APIRouter
from app.api.v1.health import router as health_router
from app.api.v1.patients import router as patients_router
from app.api.v1.simulation import router as simulation_router
from app.api.v1.websockets import router as websockets_router

api_v1_router = APIRouter()
api_v1_router.include_router(health_router, tags=["Health"])
api_v1_router.include_router(patients_router, tags=["Patients"])
api_v1_router.include_router(simulation_router, tags=["Simulation Control"])
api_v1_router.include_router(websockets_router, tags=["Streaming"])
