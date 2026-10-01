"""
ARGUS Simulation Clock Subsystem.

Provides monotonic time tracking, variable speed acceleration (1x, 5x, 10x, 30x, 60x),
and deterministic simulation time advancement.
"""

import time
from datetime import datetime, timedelta, timezone
from enum import Enum
from typing import Callable, Optional, Set
from pydantic import BaseModel, Field


class ClockState(str, Enum):
    STOPPED = "stopped"
    RUNNING = "running"
    PAUSED = "paused"


SUPPORTED_SPEEDS: Set[float] = {1.0, 5.0, 10.0, 30.0, 60.0}


class SimulationClockStatus(BaseModel):
    state: ClockState = Field(..., description="Current clock execution state")
    speed_factor: float = Field(..., description="Active simulation speed multiplier")
    wall_clock_time: datetime = Field(..., description="Current system wall-clock time UTC")
    simulation_time: datetime = Field(..., description="Current virtual simulation time UTC")
    elapsed_sim_seconds: float = Field(..., description="Total simulated seconds elapsed")
    elapsed_wall_seconds: float = Field(..., description="Total real wall seconds elapsed")


class SimulationClock:
    """
    Precision Simulation Clock.
    Calculates virtual simulation time dynamically using monotonic clock references
    to prevent timestamp drift and ensure strict monotonicity.
    """

    def __init__(
        self,
        initial_simulation_time: Optional[datetime] = None,
        speed_factor: float = 1.0,
        time_provider: Callable[[], float] = time.monotonic,
        wall_clock_provider: Callable[[], datetime] = lambda: datetime.now(timezone.utc),
    ):
        self._time_provider = time_provider
        self._wall_clock_provider = wall_clock_provider

        self._state: ClockState = ClockState.STOPPED
        self.set_speed(speed_factor)

        init_dt = initial_simulation_time or self._wall_clock_provider()
        if init_dt.tzinfo is None:
            init_dt = init_dt.replace(tzinfo=timezone.utc)
        else:
            init_dt = init_dt.astimezone(timezone.utc)
        self._initial_sim_time: datetime = init_dt

        self._accumulated_sim_seconds: float = 0.0
        self._accumulated_wall_seconds: float = 0.0
        self._last_state_change_monotonic: float = self._time_provider()

    @property
    def state(self) -> ClockState:
        return self._state

    @property
    def speed_factor(self) -> float:
        return self._speed_factor

    def set_speed(self, speed: float) -> float:
        """
        Updates simulation speed multiplier.
        Accumulates elapsed time at the old speed before applying the new speed factor.
        """
        if speed <= 0.0:
            raise ValueError(f"Speed factor must be positive, got {speed}")

        if self._state == ClockState.RUNNING:
            self._flush_running_interval()

        self._speed_factor = float(speed)
        return self._speed_factor

    def start(self, initial_simulation_time: Optional[datetime] = None) -> datetime:
        """
        Starts or restarts the simulation clock.
        """
        if initial_simulation_time is not None:
            init_dt = initial_simulation_time
            if init_dt.tzinfo is None:
                init_dt = init_dt.replace(tzinfo=timezone.utc)
            else:
                init_dt = init_dt.astimezone(timezone.utc)
            self._initial_sim_time = init_dt
        elif self._initial_sim_time is None:
            self._initial_sim_time = self._wall_clock_provider()

        self._accumulated_sim_seconds = 0.0
        self._accumulated_wall_seconds = 0.0
        self._last_state_change_monotonic = self._time_provider()
        self._state = ClockState.RUNNING
        return self.current_simulation_time()

    def pause(self) -> datetime:
        """
        Pauses simulation time advancement.
        """
        if self._state == ClockState.RUNNING:
            self._flush_running_interval()
            self._state = ClockState.PAUSED
        return self.current_simulation_time()

    def resume(self) -> datetime:
        """
        Resumes simulation time advancement from current state.
        """
        if self._state == ClockState.PAUSED or self._state == ClockState.STOPPED:
            self._last_state_change_monotonic = self._time_provider()
            self._state = ClockState.RUNNING
        return self.current_simulation_time()

    def stop(self) -> datetime:
        """
        Stops clock execution and resets accumulated time counter.
        """
        self._accumulated_sim_seconds = 0.0
        self._accumulated_wall_seconds = 0.0
        self._last_state_change_monotonic = self._time_provider()
        self._state = ClockState.STOPPED
        return self.current_simulation_time()

    def elapsed_simulation_time(self) -> float:
        """
        Returns total virtual simulated seconds elapsed since start().
        """
        if self._state == ClockState.RUNNING:
            now_mono = self._time_provider()
            dt_wall = max(0.0, now_mono - self._last_state_change_monotonic)
            return self._accumulated_sim_seconds + (dt_wall * self._speed_factor)
        return self._accumulated_sim_seconds

    def elapsed_wall_time(self) -> float:
        """
        Returns total real wall seconds elapsed while clock was running.
        """
        if self._state == ClockState.RUNNING:
            now_mono = self._time_provider()
            dt_wall = max(0.0, now_mono - self._last_state_change_monotonic)
            return self._accumulated_wall_seconds + dt_wall
        return self._accumulated_wall_seconds

    def current_simulation_time(self) -> datetime:
        """
        Returns absolute virtual simulation timestamp in UTC.
        """
        elapsed_seconds = self.elapsed_simulation_time()
        return self._initial_sim_time + timedelta(seconds=elapsed_seconds)

    def status(self) -> SimulationClockStatus:
        """
        Returns structured status summary of current clock state.
        """
        return SimulationClockStatus(
            state=self._state,
            speed_factor=self._speed_factor,
            wall_clock_time=self._wall_clock_provider(),
            simulation_time=self.current_simulation_time(),
            elapsed_sim_seconds=self.elapsed_simulation_time(),
            elapsed_wall_seconds=self.elapsed_wall_time(),
        )

    def _flush_running_interval(self) -> None:
        """
        Flushes elapsed wall time and simulated time for current running segment.
        """
        now_mono = self._time_provider()
        dt_wall = max(0.0, now_mono - self._last_state_change_monotonic)
        self._accumulated_wall_seconds += dt_wall
        self._accumulated_sim_seconds += dt_wall * self._speed_factor
        self._last_state_change_monotonic = now_mono
