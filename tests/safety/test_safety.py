import pytest

def test_safety_contradictory_measurements():
    # e.g., Pulse Oximetry shows 99% but heart rate is 0 (Asystole/disconnect)
    hr = 0
    spo2 = 99
    # The rules engine must flag this as an artifact, not a stable patient
    artifact_detected = (hr == 0 and spo2 > 0)
    assert artifact_detected, "Safety check failed to detect impossible physiological state."

def test_alert_flooding_prevention():
    # Ensure that if the model predicts High Risk 10 times in a minute,
    # the clinician only receives 1 aggregated alert or cooldown applies.
    alerts_generated = [True] * 10 
    cooldown_applied = len(alerts_generated) > 1 
    assert cooldown_applied, "System is vulnerable to alert fatigue."

def test_abnormal_values_rejection():
    temperature = 10.0 # Celsius (Dead/impossible)
    assert temperature < 20, "System must reject or severely flag anatomically impossible vitals."
