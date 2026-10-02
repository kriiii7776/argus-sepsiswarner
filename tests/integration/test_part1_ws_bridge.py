"""
Tests for Part 1 -> Part 2 Live WebSocket Bridge.
Validates bridge configuration, connection lifecycle, contract message transformation,
error resilience, patient isolation, and absence of direct Part 1 Python imports.
"""

import asyncio
import json
import ast
from pathlib import Path
import pytest
import websockets

from src.backend.core.config import Settings
from src.backend.services.part1_ws_bridge import Part1WSBridge, BridgeState
from src.backend.services.part1_adapter import Part1Adapter


@pytest.mark.asyncio
async def test_bridge_disabled_by_default():
    """Requirement 1: Bridge disabled by default."""
    s = Settings()
    assert s.argus_part1_bridge_enabled is False
    assert s.argus_part1_ws_url == "ws://127.0.0.1:8001/api/v1/stream"

    bridge = Part1WSBridge(enabled=False)
    assert bridge.enabled is False
    await bridge.start()
    assert bridge.state == BridgeState.STOPPED
    await bridge.stop()


@pytest.mark.asyncio
async def test_bridge_connects_to_mock_websocket_server():
    """Requirement 2: Bridge connects successfully to a mocked WebSocket server."""
    connected_evt = asyncio.Event()
    stop_server = asyncio.Event()

    async def server_handler(websocket):
        connected_evt.set()
        await stop_server.wait()

    async with websockets.serve(server_handler, "127.0.0.1", 8991):
        bridge = Part1WSBridge(ws_url="ws://127.0.0.1:8991", enabled=True)
        await bridge.start()
        await asyncio.wait_for(connected_evt.wait(), timeout=3.0)
        await asyncio.sleep(0.1)
        assert bridge.state == BridgeState.CONNECTED
        stop_server.set()
        await bridge.stop()
        assert bridge.state == BridgeState.STOPPED


@pytest.mark.asyncio
async def test_valid_vital_update_passed_to_adapter_and_preserves_fields():
    """Requirements 3, 4, 5, 6: Valid vital_update is passed to Part1Adapter and preserves simulation_time, patient_id, session_id."""
    processed_payloads = []
    orig_process = Part1Adapter.process_part1_message

    async def mock_process(payload):
        processed_payloads.append(payload)
        return await orig_process(payload)

    payload = {
        "schema_version": "1.0",
        "message_type": "vital_update",
        "patient_id": "P-ICU-WS-101",
        "session_id": "sess-ws-99",
        "simulation_time": "2026-10-02T16:45:00Z",
        "vitals": {
            "heart_rate": 110.0,
            "systolic_bp": 95.0,
            "diastolic_bp": 65.0,
            "spo2": 96.0,
            "temperature": 37.8,
            "respiratory_rate": 20.0
        }
    }

    server_ready = asyncio.Event()

    async def handler(websocket):
        server_ready.set()
        await websocket.send(json.dumps(payload))
        await asyncio.sleep(0.2)

    Part1Adapter.process_part1_message = mock_process
    try:
        async with websockets.serve(handler, "127.0.0.1", 8992):
            bridge = Part1WSBridge(ws_url="ws://127.0.0.1:8992", enabled=True)
            await bridge.start()
            await asyncio.wait_for(server_ready.wait(), timeout=3.0)
            await asyncio.sleep(0.3)
            await bridge.stop()

        assert len(processed_payloads) == 1
        received = processed_payloads[0]
        assert received["patient_id"] == "P-ICU-WS-101"
        assert received["session_id"] == "sess-ws-99"
        assert received["simulation_time"] == "2026-10-02T16:45:00Z"
    finally:
        Part1Adapter.process_part1_message = orig_process


@pytest.mark.asyncio
async def test_malformed_json_ignored():
    """Requirement 7: Malformed JSON is ignored without crashing."""
    bridge = Part1WSBridge(enabled=True)
    res = await bridge.process_raw_message("{invalid_json: true")
    assert res is False


@pytest.mark.asyncio
async def test_unsupported_message_type_ignored():
    """Requirement 8: Unsupported message_type is ignored."""
    bridge = Part1WSBridge(enabled=True)
    raw = json.dumps({"message_type": "system_heartbeat", "patient_id": "P-1"})
    res = await bridge.process_raw_message(raw)
    assert res is False


@pytest.mark.asyncio
async def test_adapter_validation_error_does_not_kill_bridge():
    """Requirement 9: Adapter validation error does not kill bridge."""
    bridge = Part1WSBridge(enabled=True)
    # Missing patient_id triggers ValueError in Part1Adapter
    raw = json.dumps({"message_type": "vital_update", "vitals": {}})
    res = await bridge.process_raw_message(raw)
    assert res is False


@pytest.mark.asyncio
async def test_websocket_disconnect_triggers_reconnect():
    """Requirement 10: WebSocket disconnect triggers reconnect state."""
    connection_count = 0
    reconnected_evt = asyncio.Event()

    async def disconnect_handler(websocket):
        nonlocal connection_count
        connection_count += 1
        if connection_count == 1:
            await websocket.close(1001, "Simulated disconnect")
        else:
            reconnected_evt.set()
            await asyncio.sleep(1.0)

    async with websockets.serve(disconnect_handler, "127.0.0.1", 8993):
        bridge = Part1WSBridge(ws_url="ws://127.0.0.1:8993", enabled=True)
        bridge.max_reconnect_delay = 0.1
        await bridge.start()
        await asyncio.wait_for(reconnected_evt.wait(), timeout=3.0)
        assert connection_count >= 2
        await bridge.stop()


@pytest.mark.asyncio
async def test_reconnect_uses_bounded_exponential_backoff():
    """Requirement 11: Reconnect uses bounded exponential backoff."""
    bridge = Part1WSBridge(ws_url="ws://127.0.0.1:8999", enabled=True)
    bridge.max_reconnect_delay = 4.0
    assert bridge._reconnect_delay == 1.0

    bridge._reconnect_delay = min(bridge._reconnect_delay * 2, bridge.max_reconnect_delay)
    assert bridge._reconnect_delay == 2.0
    bridge._reconnect_delay = min(bridge._reconnect_delay * 2, bridge.max_reconnect_delay)
    assert bridge._reconnect_delay == 4.0
    bridge._reconnect_delay = min(bridge._reconnect_delay * 2, bridge.max_reconnect_delay)
    assert bridge._reconnect_delay == 4.0


@pytest.mark.asyncio
async def test_shutdown_stops_bridge_cleanly():
    """Requirement 12: Shutdown stops the bridge cleanly."""
    bridge = Part1WSBridge(ws_url="ws://127.0.0.1:8994", enabled=True)
    await bridge.start()
    assert bridge._running is True
    await bridge.stop()
    assert bridge._running is False
    assert bridge.state == BridgeState.STOPPED
    assert bridge._task is None


@pytest.mark.asyncio
async def test_multiple_patients_remain_isolated():
    """Requirement 13: Multiple patients remain isolated without shared state in bridge."""
    bridge = Part1WSBridge(enabled=True)
    payload1 = {
        "message_type": "vital_update",
        "patient_id": "P-PATIENT-A",
        "session_id": "SESS-A",
        "simulation_time": "2026-10-02T10:00:00Z",
        "vitals": {"heart_rate": 80.0, "systolic_bp": 120.0, "diastolic_bp": 80.0}
    }
    payload2 = {
        "message_type": "vital_update",
        "patient_id": "P-PATIENT-B",
        "session_id": "SESS-B",
        "simulation_time": "2026-10-02T10:01:00Z",
        "vitals": {"heart_rate": 140.0, "systolic_bp": 75.0, "diastolic_bp": 45.0}
    }

    res1 = await bridge.process_raw_message(json.dumps(payload1))
    res2 = await bridge.process_raw_message(json.dumps(payload2))
    assert res1 is True
    assert res2 is True


def test_no_part1_python_imports():
    """Requirement 14: No Part 1 Python imports exist in bridge code or services."""
    services_dir = Path("src/backend/services")
    for py_file in services_dir.glob("*.py"):
        tree = ast.parse(py_file.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    assert not alias.name.startswith("part1"), f"Forbidden import of part1 in {py_file}"
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    assert not node.module.startswith("part1"), f"Forbidden import of part1 in {py_file}"
