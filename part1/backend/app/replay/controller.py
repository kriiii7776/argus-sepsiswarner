"""
Replay Controller Subsystem.

Manages dataset playback, chronological timeline synchronization, speed multiplier control,
and streaming normalized records to WebSockets and database persistence layers.
"""

from typing import Any, List, Optional
from datetime import datetime, timezone
import asyncio

from app.schemas.contract import DataSource, VitalUpdateMessage
from app.replay.adapters import DataNormalizer, ReplayAdapter
from app.streaming.manager import stream_manager
from app.core.logging import logger


class ReplayController:
    """
    Replay Subsystem Controller.
    """

    def __init__(self, adapter: ReplayAdapter, source_type: DataSource = DataSource.CSV_REPLAY):
        self.adapter = adapter
        self.source_type = source_type
        self.messages: List[VitalUpdateMessage] = []
        self._current_index: int = 0
        self._speed_factor: float = 1.0
        self._is_playing: bool = False

    @property
    def is_playing(self) -> bool:
        return self._is_playing

    @property
    def speed_factor(self) -> float:
        return self._speed_factor

    def load(
        self,
        data_source: Any,
        patient_id: str = "P-REPLAY-01",
        session_id: str = "SESS-REPLAY-01",
    ) -> int:
        """
        Loads dataset records, normalizes into ARGUS VitalUpdateMessage contract,
        and sorts chronologically by simulation_time.
        """
        raw_records = self.adapter.load_records(data_source)
        messages: List[VitalUpdateMessage] = []

        for raw in raw_records:
            msg = DataNormalizer.normalize_record(
                raw=raw,
                patient_id=patient_id,
                session_id=session_id,
                source=self.source_type,
            )
            messages.append(msg)

        # Sort strictly chronologically by simulation_time
        messages.sort(key=lambda m: m.simulation_time)
        self.messages = messages
        self._current_index = 0
        logger.info(f"Loaded {len(self.messages)} chronologically sorted replay records.")
        return len(self.messages)

    def set_speed(self, speed_factor: float) -> float:
        if speed_factor <= 0:
            raise ValueError("Replay speed factor must be positive.")
        self._speed_factor = float(speed_factor)
        return self._speed_factor

    def step(self) -> Optional[VitalUpdateMessage]:
        """
        Advances one step in the loaded replay sequence and returns the next VitalUpdateMessage.
        """
        if self._current_index >= len(self.messages):
            return None
        msg = self.messages[self._current_index]
        self._current_index += 1
        return msg

    async def play(self, session_id: Optional[str] = None):
        """
        Asynchronously plays through the dataset, broadcasting to WebSocket clients
        at the configured simulation speed.
        """
        self._is_playing = True
        logger.info(f"Starting replay playback at {self._speed_factor}x speed...")

        try:
            while self._is_playing and self._current_index < len(self.messages):
                msg = self.step()
                if msg is None:
                    break

                # Broadcast to connected WebSocket clients
                await stream_manager.broadcast(msg, session_id=session_id or msg.session_id)

                # Delay for simulation speed control if there are subsequent records
                if self._current_index < len(self.messages):
                    next_msg = self.messages[self._current_index]
                    dt_sim = (next_msg.simulation_time - msg.simulation_time).total_seconds()
                    dt_real = max(0.01, dt_sim / self._speed_factor)
                    await asyncio.sleep(dt_real)
        finally:
            self._is_playing = False
            logger.info("Replay playback finished or paused.")

    def stop(self) -> None:
        self._is_playing = False
        self._current_index = 0
