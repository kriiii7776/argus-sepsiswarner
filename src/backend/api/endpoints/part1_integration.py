"""
Part 1 Simulator Integration API Router.

Exposes REST endpoints for ingesting Part 1 contract v1.0 vital_update messages,
enabling direct integration between Part 1 simulator stream/control and Part 2 inference.
"""

import logging
from typing import Any, Dict
from fastapi import APIRouter, HTTPException, status

from src.backend.schemas.schemas import PredictionResponse
from src.backend.services.part1_adapter import Part1Adapter

log = logging.getLogger("sepsisguard.part1_integration")
router = APIRouter(tags=["part1-integration"])


@router.post(
    "/integration/part1/ingest",
    response_model=PredictionResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Ingest Part 1 Contract v1.0 Vital Update"
)
async def ingest_part1_vital_update(payload: Dict[str, Any]):
    """
    Ingests a Part 1 Contract v1.0 vital_update payload, converts simulation_time to clinical timestamp,
    and runs full Part 2 clinical intelligence inference (31 features, calibrated model, SHAP, SmartAlertEngine).
    """
    try:
        return await Part1Adapter.process_part1_message(payload)
    except ValueError as val_err:
        log.warning("Part 1 ingestion validation error: %s", val_err)
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(val_err)
        )
    except Exception as exc:
        log.exception("Part 1 ingestion failed")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process Part 1 simulator event."
        ) from exc
