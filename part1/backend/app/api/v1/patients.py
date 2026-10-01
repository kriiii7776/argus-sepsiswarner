"""
REST API endpoints for Patient Baseline & Scenario Management.
"""

from datetime import datetime
from typing import List, Optional
from fastapi import APIRouter, HTTPException, Query, status

from app.schemas.patient import Patient, PatientStatus
from app.schemas.control import PatientCreateRequest, PatientScenarioRequest, SimulationStatusResponse
from app.services.patient_registry import patient_registry
from app.services.simulation_service import simulation_service
from app.core.exceptions import ARGUSException
from app.services.clinical_context_service import clinical_context_service

router = APIRouter()


@router.get("/replay/cohort", summary="List historical replay cohort metadata")
async def get_replay_cohort():
    """Returns presentation-only cohort metadata; never use it as model input."""
    simulation_service._historical_replay.load()
    return simulation_service._historical_replay.cohort_manifest()


@router.get("/patients", response_model=List[Patient], summary="List Simulated Patients")
async def list_patients(status_filter: Optional[PatientStatus] = Query(None, alias="status")):
    """
    Returns a list of all registered simulation patients, optionally filtered by status.
    """
    return patient_registry.list_patients(status=status_filter)


@router.get("/patients/{patient_id}", response_model=Patient, summary="Get Patient Baseline Details")
async def get_patient(patient_id: str):
    """
    Retrieves patient demographic, baseline, and status details by patient_id.
    """
    patient = patient_registry.get_patient(patient_id)
    if not patient:
        raise ARGUSException(
            code="PATIENT_NOT_FOUND",
            message=f"Patient '{patient_id}' not found.",
            status_code=status.HTTP_404_NOT_FOUND,
        )
    return patient


@router.post("/patients", response_model=Patient, status_code=status.HTTP_201_CREATED, summary="Create Patient Baseline")
async def create_patient(body: PatientCreateRequest):
    """
    Creates a new synthetic patient with a baseline distribution based on profile_type and random seed.
    """
    return patient_registry.create_patient(
        patient_id=body.patient_id,
        session_id=body.session_id,
        age=body.age,
        sex=body.sex,
        profile_type=body.profile_type,
        seed=body.seed,
    )


@router.post("/patients/{patient_id}/scenario", response_model=SimulationStatusResponse, summary="Set Patient Scenario")
async def set_patient_scenario(patient_id: str, body: PatientScenarioRequest):
    """
    Sets the active scenario trajectory state-machine for the specified patient.
    """
    return simulation_service.set_patient_scenario(patient_id, body.scenario_name)


@router.get("/patients/{patient_id}/clinical-context", summary="Get clinical context as of simulation time")
async def get_clinical_context(patient_id: str, simulation_time: Optional[datetime] = None):
    """Returns the latest laboratory/EHR result available at the requested virtual time."""
    patient = patient_registry.get_patient(patient_id)
    if not patient:
        raise ARGUSException(code="PATIENT_NOT_FOUND", message=f"Patient '{patient_id}' not found.", status_code=404)
    clock = simulation_service.clock.status()
    if patient_id.startswith("MIMIC-"):
        return simulation_service._historical_replay.clinical_update(
            patient_id, int(clock.elapsed_sim_seconds / 60)
        )
    as_of_time = simulation_time or clock.simulation_time
    return clinical_context_service.as_of(
        patient_id, patient.session_id, as_of_time, clock.elapsed_sim_seconds, simulation_service.scenario_engine.scenario_name
    )
