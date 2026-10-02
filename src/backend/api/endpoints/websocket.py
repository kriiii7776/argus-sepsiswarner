import json
import logging
from datetime import datetime, timezone
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException
from pydantic import ValidationError

from src.backend.services.event_broker import broker
from src.backend.schemas.schemas import VitalEvent
from src.backend.services.inference_service import InferenceService

log = logging.getLogger('sepsisguard.websocket')
router = APIRouter(tags=['websocket'])

async def process_ws_message(ws: WebSocket, data: str, is_stream_endpoint: bool):
    if not data or not data.strip():
        return

    try:
        payload = json.loads(data)
    except json.JSONDecodeError:
        if not is_stream_endpoint:
            # Backwards compatibility echo for legacy /ws test
            await ws.send_text(f"Message text was: {data}")
        else:
            await ws.send_text(json.dumps({
                "type": "error",
                "message": "Invalid JSON format."
            }))
        return

    if not isinstance(payload, dict):
        await ws.send_text(json.dumps({
            "type": "error",
            "message": "WebSocket message must be a JSON object."
        }))
        return

    # Check for keepalive / ping
    msg_type = payload.get("type")
    if msg_type in ("ping", "keepalive"):
        await ws.send_text(json.dumps({
            "type": "pong",
            "occurred_at": datetime.now(timezone.utc).isoformat()
        }))
        return

    # Extract event data if nested under payload or event
    event_dict = payload.get("payload") or payload.get("event") or payload

    if not isinstance(event_dict, dict) or "patient_id" not in event_dict or "timestamp" not in event_dict:
        await ws.send_text(json.dumps({
            "type": "error",
            "message": "Missing required fields: patient_id and timestamp."
        }))
        return

    try:
        event = VitalEvent.model_validate(event_dict)
    except ValidationError as ve:
        await ws.send_text(json.dumps({
            "type": "error",
            "message": f"Vital event schema validation failed: {ve.error_count()} errors."
        }))
        return

    try:
        await InferenceService.ingest(event)
    except HTTPException as he:
        await ws.send_text(json.dumps({
            "type": "error",
            "message": he.detail
        }))
    except Exception:
        log.exception("WebSocket event processing failed for patient_id=%s", getattr(event, "patient_id", "unknown"))
        await ws.send_text(json.dumps({
            "type": "error",
            "message": "Event could not be processed; no prediction created."
        }))


@router.websocket('/ws/stream')
async def websocket_stream(ws: WebSocket, user_id: str | None = None):
    await ws.accept()
    ws.state.user_id = user_id or ws.query_params.get('user_id')
    broker.subscribers.add(ws)
    try:
        while True:
            data = await ws.receive_text()
            await process_ws_message(ws, data, is_stream_endpoint=True)
    except WebSocketDisconnect:
        broker.subscribers.discard(ws)


@router.websocket('/ws')
async def websocket_endpoint(ws: WebSocket, user_id: str | None = None):
    await ws.accept()
    ws.state.user_id = user_id or ws.query_params.get('user_id')
    broker.subscribers.add(ws)
    try:
        while True:
            data = await ws.receive_text()
            await process_ws_message(ws, data, is_stream_endpoint=False)
    except WebSocketDisconnect:
        broker.subscribers.discard(ws)

