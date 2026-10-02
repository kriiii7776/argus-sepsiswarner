"""
Unit tests for SimulationClock subsystem.
"""

from datetime import datetime, timedelta, timezone
import pytest
import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.simulation.clock import ClockState, SimulationClock


class MockTimeProvider:
    def __init__(self, start_time: float = 1000.0):
        self._current_time = start_time

    def get_time(self) -> float:
        return self._current_time

    def advance(self, seconds: float):
        self._current_time += seconds


@pytest.fixture
def mock_clock():
    time_provider = MockTimeProvider(1000.0)
    init_sim_time = datetime(2026, 10, 1, 12, 0, 0, tzinfo=timezone.utc)
    clock = SimulationClock(
        initial_simulation_time=init_sim_time,
        speed_factor=1.0,
        time_provider=time_provider.get_time,
    )
    return clock, time_provider, init_sim_time


def test_initial_stopped_state(mock_clock):
    clock, _, init_sim_time = mock_clock
    assert clock.state == ClockState.STOPPED
    assert clock.current_simulation_time() == init_sim_time
    assert clock.elapsed_simulation_time() == 0.0


@pytest.mark.parametrize("speed", [1.0, 5.0, 10.0, 30.0, 60.0])
def test_simulation_speeds(mock_clock, speed):
    clock, time_provider, init_sim_time = mock_clock
    clock.set_speed(speed)
    clock.start()

    # Advance wall clock by 10 real seconds
    time_provider.advance(10.0)

    expected_sim_seconds = 10.0 * speed
    assert clock.elapsed_simulation_time() == pytest.approx(expected_sim_seconds)
    assert clock.current_simulation_time() == init_sim_time + timedelta(seconds=expected_sim_seconds)


def test_invalid_speed_factor(mock_clock):
    clock, _, _ = mock_clock
    with pytest.raises(ValueError):
        clock.set_speed(0.0)
    with pytest.raises(ValueError):
        clock.set_speed(-5.0)


def test_pause_and_resume(mock_clock):
    clock, time_provider, init_sim_time = mock_clock
    clock.start()

    # Run for 5 real seconds at 1x -> 5 sim seconds
    time_provider.advance(5.0)
    assert clock.elapsed_simulation_time() == pytest.approx(5.0)

    # Pause clock
    clock.pause()
    assert clock.state == ClockState.PAUSED

    # Advance real time by 20 seconds while paused
    time_provider.advance(20.0)
    assert clock.elapsed_simulation_time() == pytest.approx(5.0)
    assert clock.current_simulation_time() == init_sim_time + timedelta(seconds=5.0)

    # Resume clock
    clock.resume()
    assert clock.state == ClockState.RUNNING

    # Advance real time by 10 seconds while running -> should add 10 sim seconds to previous 5 sim seconds
    time_provider.advance(10.0)
    assert clock.elapsed_simulation_time() == pytest.approx(15.0)
    assert clock.current_simulation_time() == init_sim_time + timedelta(seconds=15.0)


def test_stop_resets_simulation(mock_clock):
    clock, time_provider, init_sim_time = mock_clock
    clock.start()
    time_provider.advance(15.0)
    assert clock.elapsed_simulation_time() == pytest.approx(15.0)

    clock.stop()
    assert clock.state == ClockState.STOPPED
    assert clock.elapsed_simulation_time() == 0.0


def test_speed_change_mid_simulation(mock_clock):
    clock, time_provider, init_sim_time = mock_clock
    clock.start()
    clock.set_speed(1.0)

    # Run 10s at 1x -> 10 sim seconds
    time_provider.advance(10.0)
    assert clock.elapsed_simulation_time() == pytest.approx(10.0)

    # Change speed to 10x
    clock.set_speed(10.0)

    # Verify sim time didn't reset on speed change
    assert clock.elapsed_simulation_time() == pytest.approx(10.0)

    # Run 2 real seconds at 10x -> 20 sim seconds
    time_provider.advance(2.0)
    assert clock.elapsed_simulation_time() == pytest.approx(30.0)
    assert clock.current_simulation_time() == init_sim_time + timedelta(seconds=30.0)


def test_strict_monotonic_simulation_time(mock_clock):
    clock, time_provider, _ = mock_clock
    clock.start()
    clock.set_speed(5.0)

    prev_time = clock.current_simulation_time()

    for step in [0.1, 0.5, 1.0, 5.0, 10.0]:
        time_provider.advance(step)
        curr_time = clock.current_simulation_time()
        assert curr_time >= prev_time
        prev_time = curr_time


def test_status_summary(mock_clock):
    clock, time_provider, init_sim_time = mock_clock
    clock.set_speed(5.0)
    clock.start()
    time_provider.advance(4.0)

    status = clock.status()
    assert status.state == ClockState.RUNNING
    assert status.speed_factor == 5.0
    assert status.elapsed_wall_seconds == pytest.approx(4.0)
    assert status.elapsed_sim_seconds == pytest.approx(20.0)
    assert status.simulation_time == init_sim_time + timedelta(seconds=20.0)
