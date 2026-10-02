from fastapi import APIRouter
from src.backend.core.config import settings
from src.backend.services.inference_runtime import runtime
from src.backend.schemas.schemas import ModelVersionResponse

router = APIRouter()

@router.get("/health")
def health_check():
    return {"status": "healthy"}

@router.get("/model-version", response_model=ModelVersionResponse)
def get_model_version():
    return ModelVersionResponse(
        model_version=runtime.model_version_name,
        is_demo_model=runtime.demo,
        prediction_horizon_hours=6
    )
