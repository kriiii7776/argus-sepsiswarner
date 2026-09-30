from fastapi import APIRouter
from src.backend.api.endpoints import patients, health

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(patients.router, tags=["patients"])
