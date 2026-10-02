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
    
    # Auto-seed canonical demo patients (PATIENT-001..PATIENT-004) if missing
    from app.services.patient_registry import patient_registry
    from app.schemas.patient import PatientProfileType, PatientSex
    from app.services.simulation_service import simulation_service
    from app.simulation.scenario_engine import ScenarioName

    canonical_specs = [
        ("PATIENT-001", "LIVE-TEST-001", 65, PatientSex.MALE, PatientProfileType.ICU_BASELINE, ScenarioName.RAPID_DETERIORATION, 42),
        ("PATIENT-002", "LIVE-TEST-002", 58, PatientSex.FEMALE, PatientProfileType.ICU_BASELINE, ScenarioName.STABLE, 101),
        ("PATIENT-003", "LIVE-TEST-003", 72, PatientSex.MALE, PatientProfileType.GERIATRIC, ScenarioName.GRADUAL_DETERIORATION, 202),
        ("PATIENT-004", "LIVE-TEST-004", 45, PatientSex.FEMALE, PatientProfileType.STANDARD, ScenarioName.STABLE, 303),
    ]

    for pid, sid, age, sex, profile, scenario, seed in canonical_specs:
        patient = patient_registry.get_patient(pid)
        if not patient:
            try:
                patient_registry.create_patient(
                    patient_id=pid,
                    session_id=sid,
                    age=age,
                    sex=sex,
                    profile_type=profile,
                    seed=seed,
                )
                logger.info(f"Auto-seeded demo patient: {pid}")
            except Exception as e:
                logger.warning(f"Demo patient creation skipped for {pid}: {e}")

    try:
        mimic_patients = simulation_service._historical_replay.load()
        for mp in mimic_patients:
            if not patient_registry.get_patient(mp.patient_id):
                patient_registry.register_patient(mp)
        logger.info(f"Auto-registered {len(mimic_patients)} MIMIC historical replay patients")
    except Exception as e:
        logger.warning(f"Failed to auto-register MIMIC replay patients: {e}")

    if settings.DEMO_MODE:
        try:
            for pid, sid, _, _, _, scenario, _ in canonical_specs:
                simulation_service.set_patient_scenario(pid, scenario)
                simulation_service.start_simulation(
                    patient_id=pid,
                    session_id=sid,
                    speed_factor=settings.DEMO_SPEED_FACTOR,
                )
            logger.info(f"DEMO_MODE active: Auto-started simulations for canonical patients ({settings.DEMO_SPEED_FACTOR}x speed)")
        except Exception as e:
            logger.error(f"Failed to auto-start DEMO simulations: {e}")

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
