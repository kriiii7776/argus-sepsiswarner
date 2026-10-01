from fastapi import APIRouter
from src.backend.api.endpoints import patients, health, events, websocket

api_router = APIRouter()
api_router.include_router(health.router, tags=["health"])
api_router.include_router(patients.router, tags=["patients"])
api_router.include_router(events.router, tags=["events"])
api_router.include_router(websocket.router, tags=["websocket"])
