"""
ARGUS Alert Router Service (Track B)

Routes Part 2 SmartAlertEngine alert events to assigned care-team members (doctors/nurses)
and their registered mobile/desktop devices, enforcing patient isolation and tracking
acknowledgement lifecycle without altering ML probabilities or threshold logic.
"""

from datetime import datetime, timezone
import logging
from typing import List, Dict, Any, Optional

from src.backend.db.store import (
    Session, StaffRecord, PatientAssignmentRecord, DeviceRegistrationRecord, AlertAcknowledgementRecord
)
from src.backend.services.event_broker import broker

log = logging.getLogger('sepsisguard.alert_router')


class AlertRouter:
    """
    Care-team alert router mapping patient clinical events to responsible staff & devices.
    """

    @staticmethod
    def get_assigned_staff_for_patient(patient_id: str) -> List[Dict[str, Any]]:
        """Return list of staff users assigned to a patient."""
        with Session() as s:
            assignments = s.query(PatientAssignmentRecord).filter(
                PatientAssignmentRecord.patient_id == patient_id
            ).all()
            user_ids = [a.user_id for a in assignments]
            if not user_ids:
                return []
            staff = s.query(StaffRecord).filter(
                StaffRecord.user_id.in_(user_ids),
                StaffRecord.active == True
            ).all()
            return [
                {
                    'user_id': u.user_id,
                    'name': u.name,
                    'role': u.role,
                    'assigned_unit': u.assigned_unit
                }
                for u in staff
            ]

    @staticmethod
    def get_assigned_patients_for_user(user_id: str) -> List[str]:
        """Return list of patient IDs assigned to a staff user."""
        with Session() as s:
            staff = s.query(StaffRecord).filter(StaffRecord.user_id == user_id).first()
            # ICU_ADMIN or unconstrained role sees all assigned patients
            if staff and staff.role == 'ICU_ADMIN':
                from src.backend.db.store import PatientRecord
                patients = s.query(PatientRecord.patient_id).all()
                return [p.patient_id for p in patients]
            
            assignments = s.query(PatientAssignmentRecord).filter(
                PatientAssignmentRecord.user_id == user_id
            ).all()
            return [a.patient_id for a in assignments]

    @staticmethod
    def is_user_authorized_for_patient(user_id: str, patient_id: str) -> bool:
        """Check if staff user is authorized to access a patient."""
        if not user_id or user_id == 'system' or user_id == 'admin':
            return True
        with Session() as s:
            staff = s.query(StaffRecord).filter(StaffRecord.user_id == user_id).first()
            if staff and staff.role == 'ICU_ADMIN':
                return True
            assignment = s.query(PatientAssignmentRecord).filter(
                PatientAssignmentRecord.user_id == user_id,
                PatientAssignmentRecord.patient_id == patient_id
            ).first()
            return assignment is not None

    @staticmethod
    def get_registered_devices_for_users(user_ids: List[str]) -> List[Dict[str, Any]]:
        """Return list of active registered devices for a set of staff users."""
        if not user_ids:
            return []
        with Session() as s:
            devices = s.query(DeviceRegistrationRecord).filter(
                DeviceRegistrationRecord.user_id.in_(user_ids),
                DeviceRegistrationRecord.active == True
            ).all()
            return [
                {
                    'device_id': d.device_id,
                    'user_id': d.user_id,
                    'platform': d.platform,
                    'push_token': d.push_token,
                    'last_seen': d.last_seen.isoformat() if d.last_seen else None
                }
                for d in devices
            ]

    @classmethod
    async def route_alert(cls, patient_id: str, alert_payload: Dict[str, Any]) -> Dict[str, Any]:
        """
        Routes an alert emitted by SmartAlertEngine to assigned care team members & devices.
        """
        care_team = cls.get_assigned_staff_for_patient(patient_id)
        target_user_ids = [member['user_id'] for member in care_team]
        target_devices = cls.get_registered_devices_for_users(target_user_ids)
        target_device_ids = [d['device_id'] for d in target_devices]

        ts_str = datetime.now(timezone.utc).isoformat()
        alert_id = alert_payload.get('alert_id') or f"alert-{patient_id}-{int(datetime.now(timezone.utc).timestamp())}"
        severity = alert_payload.get('alert_severity') or alert_payload.get('severity') or 'NONE'

        routed_payload = {
            'alert_id': alert_id,
            'patient_id': patient_id,
            'session_id': alert_payload.get('session_id'),
            'severity': severity,
            'recommended_clinical_review_level': alert_payload.get('recommended_clinical_review_level', 'No alert'),
            'risk_probability': alert_payload.get('risk_probability'),
            'target_users': target_user_ids,
            'target_devices': target_device_ids,
            'care_team': care_team,
            'vitals': alert_payload.get('vitals'),
            'timestamp': alert_payload.get('prediction_timestamp') or ts_str,
            'status': 'EMITTED'
        }

        # Store alert acknowledgement state in database
        with Session.begin() as s:
            existing = s.query(AlertAcknowledgementRecord).filter(
                AlertAcknowledgementRecord.alert_id == alert_id
            ).first()
            if not existing:
                s.add(AlertAcknowledgementRecord(
                    alert_id=alert_id,
                    patient_id=patient_id,
                    severity=severity,
                    status='EMITTED',
                    created_at=datetime.now(timezone.utc)
                ))

        log.info(
            "Routed alert %s for patient %s (severity=%s) to users=%s devices=%s",
            alert_id, patient_id, severity, target_user_ids, target_device_ids
        )

        await broker.publish('routed_alert', patient_id, routed_payload)
        return routed_payload

    @classmethod
    async def acknowledge_alert(cls, alert_id: str, user_id: str) -> Dict[str, Any]:
        """
        Acknowledges an alert by a staff member and broadcasts status update.
        """
        now_dt = datetime.now(timezone.utc)
        patient_id = "unknown"
        severity = "NONE"

        with Session.begin() as s:
            ack = s.query(AlertAcknowledgementRecord).filter(
                AlertAcknowledgementRecord.alert_id == alert_id
            ).first()
            if ack:
                ack.status = 'ACKNOWLEDGED'
                ack.user_id = user_id
                ack.acknowledged_at = now_dt
                patient_id = ack.patient_id
                severity = ack.severity
            else:
                ack = AlertAcknowledgementRecord(
                    alert_id=alert_id,
                    patient_id=patient_id,
                    user_id=user_id,
                    severity=severity,
                    status='ACKNOWLEDGED',
                    created_at=now_dt,
                    acknowledged_at=now_dt
                )
                s.add(ack)

        ack_payload = {
            'alert_id': alert_id,
            'patient_id': patient_id,
            'user_id': user_id,
            'severity': severity,
            'status': 'ACKNOWLEDGED',
            'acknowledged_at': now_dt.isoformat()
        }

        log.info("Alert %s acknowledged by user %s", alert_id, user_id)
        await broker.publish('alert_acknowledged', patient_id, ack_payload)
        return ack_payload


alert_router = AlertRouter()
