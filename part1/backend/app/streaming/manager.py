"""
WebSocket Connection Manager.

Handles client registration, session-based filtering, thread-safe broadcasting,
disconnection handling, and multi-client connection pooling.
"""

from typing import Dict, List, Optional
from fastapi import WebSocket
from app.schemas.contract import BaseMessage
from app.core.logging import logger


class ConnectionManager:
    """
    Real-time WebSocket Connection and Broadcast Manager.
    """

    def __init__(self):
        # Maps active WebSocket connection to optional target session_id filter
        self._active_connections: Dict[WebSocket, Optional[str]] = {}

    @property
    def connection_count(self) -> int:
        return len(self._active_connections)

    async def connect(self, websocket: WebSocket, session_id: Optional[str] = None) -> None:
        """
        Accepts and registers an incoming WebSocket connection.
        """
        await websocket.accept()
        self._active_connections[websocket] = session_id
        logger.info(f"WebSocket client connected (session_id={session_id}). Active count: {self.connection_count}")

    def disconnect(self, websocket: WebSocket) -> None:
        """
        Unregisters a disconnected WebSocket client socket.
        """
        if websocket in self._active_connections:
            del self._active_connections[websocket]
            logger.info(f"WebSocket client disconnected. Remaining count: {self.connection_count}")

    async def send_personal_message(self, message: BaseMessage, websocket: WebSocket) -> None:
        """
        Sends a JSON message payload directly to a specific connected client.
        """
        payload = message.model_dump_json()
        await websocket.send_text(payload)

    async def broadcast(self, message: BaseMessage, session_id: Optional[str] = None) -> int:
        """
        Broadcasts a contract-compliant BaseMessage payload to all matching connected clients.
        Returns the count of successful transmissions.
        """
        payload = message.model_dump_json()
        stale_connections: List[WebSocket] = []
        delivered_count = 0

        for ws, client_session in list(self._active_connections.items()):
            # Deliver if client requested all sessions (None) or matching session_id
            if client_session is None or session_id is None or client_session == session_id:
                try:
                    await ws.send_text(payload)
                    delivered_count += 1
                except Exception as exc:
                    logger.warning(f"Error broadcasting message to WebSocket client: {exc}")
                    stale_connections.append(ws)

        for ws in stale_connections:
            self.disconnect(ws)

        return delivered_count

    async def disconnect_all(self) -> None:
        """
        Gracefully closes all active client WebSocket connections.
        """
        for ws in list(self._active_connections.keys()):
            try:
                await ws.close()
            except Exception:
                pass
        self._active_connections.clear()


stream_manager = ConnectionManager()
