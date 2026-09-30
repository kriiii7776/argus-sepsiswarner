from fastapi import APIRouter
from src.backend.core.config import settings

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "healthy"}

@router.get("/model-version")
def get_model_version():
    return {"model_version": settings.MODEL_VERSION}
