"""
REST API endpoints for Simulation Clock and Session Control.
"""

from typing import Optional
from fastapi import APIRouter, status

from app.schemas.control import (
    SimulationSpeedRequest,
    SimulationStartRequest,
    SimulationStatusResponse,
)
from app.services.simulation_service import simulation_service

router = APIRouter()


@router.post("/simulation/start", response_model=SimulationStatusResponse, summary="Start Simulation Session")
async def start_simulation(body: Optional[SimulationStartRequest] = None):
    """
    Starts or restarts the simulation clock and active session.
    """
    req = body or SimulationStartRequest()
    return simulation_service.start_simulation(
        session_id=req.session_id,
        patient_id=req.patient_id,
        speed_factor=req.speed_factor,
        initial_simulation_time=req.initial_simulation_time,
    )


@router.post("/simulation/pause", response_model=SimulationStatusResponse, summary="Pause Simulation Clock")
async def pause_simulation():
    """
    Pauses virtual simulation time advancement.
    """
    return simulation_service.pause_simulation()


@router.post("/simulation/resume", response_model=SimulationStatusResponse, summary="Resume Simulation Clock")
async def resume_simulation():
    """
    Resumes virtual simulation time advancement.
    """
    return simulation_service.resume_simulation()


@router.post("/simulation/stop", response_model=SimulationStatusResponse, summary="Stop Simulation Clock")
async def stop_simulation():
    """
    Stops virtual simulation clock and resets active scenario trajectory.
    """
    return simulation_service.stop_simulation()


@router.post("/simulation/speed", response_model=SimulationStatusResponse, summary="Set Simulation Speed")
async def set_simulation_speed(body: SimulationSpeedRequest):
    """
    Sets simulation clock speed multiplier (e.g. 1.0, 5.0, 10.0, 30.0, 60.0).
    """
    return simulation_service.set_speed(body.speed_factor)


@router.get("/simulation/status", response_model=SimulationStatusResponse, summary="Get Simulation Status Summary")
async def get_simulation_status():
    """
    Returns full runtime status summary including clock state, speed factor, active patient/session, and active scenario.
    """
    return simulation_service.get_status()
