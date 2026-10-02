"""
Main FastAPI Application Entrypoint for ARGUS Data Source & Simulation Platform.
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import (
    ARGUSException,
    argus_exception_handler,
    generic_exception_handler,
    validation_exception_handler,
)
from app.api.v1.router import api_v1_router
from app.api.v1.health import get_health, HealthResponse


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(f"Starting {settings.PROJECT_NAME} v{settings.VERSION} [{settings.ENVIRONMENT}]")
    
    # Auto-seed PATIENT-001 if missing
    from app.services.patient_registry import patient_registry
    from app.schemas.patient import PatientProfileType, PatientSex

    demo_patient = patient_registry.get_patient(settings.DEMO_PATIENT_ID)
    if not demo_patient:
        try:
            demo_patient = patient_registry.create_patient(
                patient_id=settings.DEMO_PATIENT_ID,
                session_id="LIVE-TEST-001",
                age=65,
                sex=PatientSex.MALE,
                profile_type=PatientProfileType.ICU_BASELINE,
                seed=42,
            )
            logger.info(f"Auto-seeded demo patient: {settings.DEMO_PATIENT_ID}")
        except Exception as e:
            logger.warning(f"Demo patient creation skipped: {e}")

    if settings.DEMO_MODE:
        from app.services.simulation_service import simulation_service
        from app.simulation.scenario_engine import ScenarioName
        try:
            simulation_service.set_patient_scenario(settings.DEMO_PATIENT_ID, ScenarioName.RAPID_DETERIORATION)
            simulation_service.start_simulation(
                patient_id=settings.DEMO_PATIENT_ID,
                session_id="LIVE-TEST-001",
                speed_factor=settings.DEMO_SPEED_FACTOR,
            )
            logger.info(f"DEMO_MODE active: Auto-started simulation for {settings.DEMO_PATIENT_ID} ({settings.DEMO_SPEED_FACTOR}x speed)")
        except Exception as e:
            logger.error(f"Failed to auto-start DEMO simulation: {e}")

    yield
    logger.info(f"Shutting down {settings.PROJECT_NAME}")


app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="ARGUS Part 1 — Synthetic ICU Patient Simulation & Real-Time Data Source Layer",
    openapi_url=f"{settings.API_V1_STR}/openapi.json",
    docs_url=f"{settings.API_V1_STR}/docs",
    redoc_url=f"{settings.API_V1_STR}/redoc",
    lifespan=lifespan,
)

# CORS Middleware Setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exception Handlers
app.add_exception_handler(ARGUSException, argus_exception_handler)
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Top-level Health Check Endpoint
app.add_api_route("/health", get_health, methods=["GET"], response_model=HealthResponse, tags=["Health"])

# Include API v1 Router Architecture
app.include_router(api_v1_router, prefix=settings.API_V1_STR)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
