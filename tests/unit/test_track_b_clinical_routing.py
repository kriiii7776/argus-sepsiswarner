import pytest
import asyncio
from datetime import datetime, timezone
from src.backend.db.store import init_db, Session, StaffRecord, PatientAssignmentRecord, DeviceRegistrationRecord, AlertAcknowledgementRecord
from src.backend.services.alert_router import alert_router


@pytest.fixture(autouse=True)
def setup_test_db():
    init_db()


def test_staff_and_assignment_lookup():
    staff = alert_router.get_assigned_staff_for_patient('PATIENT-001')
    user_ids = [s['user_id'] for s in staff]
    assert 'USER-001' in user_ids
    assert 'USER-002' in user_ids
    assert 'USER-003' not in user_ids

    patient_ids = alert_router.get_assigned_patients_for_user('USER-001')
    assert 'PATIENT-001' in patient_ids
    assert 'PATIENT-002' in patient_ids
    assert 'PATIENT-003' not in patient_ids


def test_patient_isolation_authorization():
    assert alert_router.is_user_authorized_for_patient('USER-001', 'PATIENT-001') is True
    assert alert_router.is_user_authorized_for_patient('USER-003', 'PATIENT-001') is False
    assert alert_router.is_user_authorized_for_patient('USER-003', 'PATIENT-003') is True


def test_device_registration_lookup():
    devices = alert_router.get_registered_devices_for_users(['USER-001', 'USER-002'])
    device_ids = [d['device_id'] for d in devices]
    assert 'DEVICE-001' in device_ids
    assert 'DEVICE-002' in device_ids
    assert 'DEVICE-003' not in device_ids


@pytest.mark.asyncio
async def test_alert_router_routing_and_acknowledgement():
    alert_payload = {
        'alert_id': 'test-alert-001',
        'patient_id': 'PATIENT-001',
        'session_id': 'session-001',
        'alert_severity': 'RED_URGENT',
        'recommended_clinical_review_level': 'Urgent clinical review',
        'risk_probability': 0.86,
        'prediction_timestamp': datetime.now(timezone.utc).isoformat()
    }

    routed = await alert_router.route_alert('PATIENT-001', alert_payload)
    assert routed['alert_id'] == 'test-alert-001'
    assert routed['patient_id'] == 'PATIENT-001'
    assert 'USER-001' in routed['target_users']
    assert 'USER-002' in routed['target_users']
    assert 'USER-003' not in routed['target_users']
    assert 'DEVICE-001' in routed['target_devices']
    assert 'DEVICE-003' not in routed['target_devices']

    ack = await alert_router.acknowledge_alert('test-alert-001', 'USER-002')
    assert ack['alert_id'] == 'test-alert-001'
    assert ack['user_id'] == 'USER-002'
    assert ack['status'] == 'ACKNOWLEDGED'
