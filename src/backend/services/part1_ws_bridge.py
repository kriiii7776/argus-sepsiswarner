"""
ARGUS Part 1 Simulator to Part 2 Clinical Intelligence Live WebSocket Bridge.

Connects to Part 1 Simulator WebSocket stream (e.g., ws://127.0.0.1:8001/api/v1/stream)
and forwards vital_update contract v1.0 payloads directly into Part 1 Adapter's
process_part1_message() pipeline without modifying Part 1 code, Part 2 ML models, or database schemas.
"""

import asyncio
from enum import Enum
import json
import logging
from typing import Any, Dict, Optional
import websockets
from websockets.exceptions import ConnectionClosed

from src.backend.core.config import settings
from src.backend.services.part1_adapter import Part1Adapter

logger = logging.getLogger("sepsisguard.part1_ws_bridge")


class BridgeState(str, Enum):
    STOPPED = "STOPPED"
    STARTING = "STARTING"
    CONNECTED = "CONNECTED"
    RECONNECTING = "RECONNECTING"
    ERROR = "ERROR"


class Part1WSBridge:
    """
    Asynchronous WebSocket Bridge consuming Part 1 simulator vital_update messages
    and piping them to Part 1 Adapter for Part 2 clinical intelligence inference.
    """

    def __init__(self, ws_url: Optional[str] = None, enabled: Optional[bool] = None):
        self._ws_url = ws_url
        self._enabled = enabled
        self.state: BridgeState = BridgeState.STOPPED
        self._task: Optional[asyncio.Task] = None
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running: bool = False
        self._reconnect_delay: float = 1.0
        self.max_reconnect_delay: float = 30.0

    @property
    def ws_url(self) -> str:
        if self._ws_url is not None:
            return self._ws_url
        return getattr(settings, "ARGUS_PART1_WS_URL", "ws://127.0.0.1:8001/api/v1/stream")

    @property
    def enabled(self) -> bool:
        if self._enabled is not None:
            return self._enabled
        return getattr(settings, "ARGUS_PART1_BRIDGE_ENABLED", False)

    async def start(self) -> None:
        """Starts the WebSocket bridge background consumer loop if enabled."""
        if not self.enabled:
            logger.info("ARGUS Part1 bridge disabled")
            self.state = BridgeState.STOPPED
            return

        if self._running:
            return

        self._running = True
        self.state = BridgeState.STARTING
        logger.info("ARGUS Part1 bridge starting: %s", self.ws_url)
        self._task = asyncio.create_task(self._run_loop())

    async def stop(self) -> None:
        """Stops the bridge loop and closes open WebSocket connections cleanly."""
        self._running = False
        self.state = BridgeState.STOPPED
        if self._ws:
            try:
                await self._ws.close()
            except Exception as exc:
                logger.debug("Error closing bridge WebSocket: %s", exc)
            self._ws = None

        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            self._task = None

        logger.info("ARGUS Part1 bridge stopped")

    async def _run_loop(self) -> None:
        self._reconnect_delay = 1.0
        while self._running:
            try:
                logger.debug("Connecting to Part 1 WebSocket at %s", self.ws_url)
                async with websockets.connect(self.ws_url) as ws:
                    self._ws = ws
                    self.state = BridgeState.CONNECTED
                    logger.info("ARGUS Part1 bridge connected")
                    self._reconnect_delay = 1.0  # Reset backoff on successful connection

                    while self._running:
                        try:
                            message = await ws.recv()
                        except ConnectionClosed:
                            logger.warning("ARGUS Part1 bridge WebSocket connection closed")
                            break

                        await self.process_raw_message(message)

            except asyncio.CancelledError:
                break
            except Exception as exc:
                if not self._running:
                    break
                logger.warning("ARGUS Part1 bridge connection error: %s", exc)

            self._ws = None
            if not self._running:
                break

            self.state = BridgeState.RECONNECTING
            logger.info("ARGUS Part1 bridge reconnecting in %d seconds", int(self._reconnect_delay))
            try:
                await asyncio.sleep(self._reconnect_delay)
            except asyncio.CancelledError:
                break

            self._reconnect_delay = min(self._reconnect_delay * 2, self.max_reconnect_delay)

    async def process_raw_message(self, raw_message: str | bytes) -> bool:
        """
        Parses and validates a raw WebSocket message string/bytes, passing vital_updates to Part1Adapter.
        Returns True if successfully processed, False if skipped or errored.
        """
        try:
            payload = json.loads(raw_message)
        except (json.JSONDecodeError, TypeError) as err:
            logger.warning("ARGUS Part1 bridge received malformed JSON: %s", err)
            return False

        if not isinstance(payload, dict):
            logger.warning("ARGUS Part1 bridge payload is not a JSON object")
            return False

        msg_type = payload.get("message_type")
        if msg_type not in ("vital_update", "clinical_update"):
            logger.debug("ARGUS Part1 bridge ignoring message_type '%s'", msg_type)
            return False

        try:
            await Part1Adapter.process_part1_message(payload)
            return True
        except ValueError as val_err:
            logger.warning("ARGUS Part1 bridge adapter validation warning: %s", val_err)
            return False
        except Exception as exc:
            logger.exception("ARGUS Part1 bridge inference processing exception: %s", exc)
            return False


# Global singleton instance for application lifecycle
part1_bridge = Part1WSBridge()
