"""
WebSocket API Endpoints for ARGUS Data Stream.

Serves real-time contract-compliant telemetry and event messages over WebSockets.
"""

from typing import Optional
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from app.streaming.manager import stream_manager
from app.core.logging import logger

router = APIRouter()


@router.websocket("/stream")
async def websocket_stream_endpoint(websocket: WebSocket, session_id: Optional[str] = None):
    """
    WebSocket streaming endpoint: ws://<host>:<port>/api/v1/stream?session_id=SESS-XXX
    Streams real-time vital updates and simulation events.
    """
    await stream_manager.connect(websocket, session_id=session_id)
    try:
        while True:
            # Keep connection alive & receive optional client heartbeats/messages
            data = await websocket.receive_text()
            logger.debug(f"Received WebSocket message from client: {data}")
    except WebSocketDisconnect:
        stream_manager.disconnect(websocket)
    except Exception as exc:
        logger.warning(f"WebSocket client error: {exc}")
        stream_manager.disconnect(websocket)


@router.websocket("/stream/{session_id}")
async def websocket_session_stream_endpoint(websocket: WebSocket, session_id: str):
    """
    WebSocket session streaming endpoint: ws://<host>:<port>/api/v1/stream/{session_id}
    """
    await websocket_stream_endpoint(websocket, session_id=session_id)
