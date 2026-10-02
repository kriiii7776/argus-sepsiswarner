from datetime import datetime, timedelta, timezone
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent / "backend"))

from app.services.clinical_context_service import ClinicalContextService
from app.simulation.scenario_engine import ScenarioName


def test_clinical_context_uses_only_results_available_as_of_requested_time():
    service = ClinicalContextService()
    start = datetime(2026, 10, 1, 8, 0, tzinfo=timezone.utc)

    initial = service.as_of("P-1", "S-1", start, 0, ScenarioName.GRADUAL_DETERIORATION)
    before_next_result = service.as_of("P-1", "S-1", start + timedelta(seconds=59), 59, ScenarioName.GRADUAL_DETERIORATION)
    after_next_result = service.as_of("P-1", "S-1", start + timedelta(seconds=120), 120, ScenarioName.GRADUAL_DETERIORATION)

    assert initial.recorded_at == start
    assert before_next_result.recorded_at == start
    assert after_next_result.recorded_at == start + timedelta(seconds=120)
    assert after_next_result.clinical_context.lactate > initial.clinical_context.lactate
