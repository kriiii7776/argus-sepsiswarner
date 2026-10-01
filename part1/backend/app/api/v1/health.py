"""
Health check endpoint router.
"""

from datetime import datetime, timezone
from fastapi import APIRouter
from pydantic import BaseModel, Field
from app.core.config import settings

router = APIRouter()


class HealthResponse(BaseModel):
    status: str = Field("healthy", description="Service operational status")
    service: str = Field(..., description="Service name")
    version: str = Field(..., description="Service version")
    environment: str = Field(..., description="Active environment")
    timestamp: datetime = Field(..., description="UTC timestamp of response")


@router.get("/health", response_model=HealthResponse, summary="Get Service Health Status")
async def get_health():
    """
    Returns service health status, version, environment, and timestamp.
    """
    return HealthResponse(
        status="healthy",
        service=settings.PROJECT_NAME,
        version=settings.VERSION,
        environment=settings.ENVIRONMENT,
        timestamp=datetime.now(timezone.utc),
    )
