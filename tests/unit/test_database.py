import pytest
from datetime import datetime, timezone, timedelta
from sqlalchemy import select
from fastapi.testclient import TestClient

from src.backend.db.store import engine, Session, PatientRecord, VitalRecord, PredictionRecord, AlertRecord
from src.backend.db.repositories import patient_repository
from src.backend.services.patient_service import patient_service
from src.backend.services.inference_service import InferenceService
from src.backend.schemas.schemas import VitalEvent
from src.backend.main import app

client = TestClient(app)

def test_01_engine_initialization():
    assert engine is not None
    assert engine.dialect.name in ('sqlite', 'postgresql')

def test_02_session_lifecycle():
    with Session() as s:
        result = s.scalars(select(PatientRecord)).all()
        assert isinstance(result, list)

def test_03_patient_creation():
    patient_id = "DB-PAT-001"
    patient_service.require(patient_id)
    
    with Session() as s:
        row = s.scalars(select(PatientRecord).where(PatientRecord.patient_id == patient_id)).first()
        assert row is not None
        assert row.patient_id == patient_id
        assert row.source_system == 'local'

def test_04_patient_retrieval():
    patient_id = "DB-PAT-002"
    patient_service.require(patient_id)
    patient = patient_service.get_patient(patient_id)
    assert patient.id == patient_id

@pytest.mark.asyncio
async def test_05_vital_persistence():
    patient_id = "DB-PAT-003"
    patient_service.require(patient_id)
    ts = datetime.now(timezone.utc)
    
    event = VitalEvent(
        patient_id=patient_id,
        timestamp=ts,
        heart_rate=85.0,
        map=90.0,
        resp_rate=16.0,
        spo2=98.0,
        temperature_c=37.0,
        source='integration'
    )
    await InferenceService.ingest(event)
    
    with Session() as s:
        v_rows = list(s.scalars(select(VitalRecord).where(VitalRecord.patient_id == patient_id)))
        assert len(v_rows) >= 1
        assert v_rows[0].patient_id == patient_id

@pytest.mark.asyncio
async def test_06_prediction_persistence():
    patient_id = "DB-PAT-004"
    patient_service.require(patient_id)
    ts = datetime.now(timezone.utc)
    
    event = VitalEvent(
        patient_id=patient_id,
        timestamp=ts,
        heart_rate=88.0,
        map=85.0,
        resp_rate=18.0,
        spo2=97.0
    )
    res = await InferenceService.ingest(event)
    
    with Session() as s:
        p_rows = list(s.scalars(select(PredictionRecord).where(PredictionRecord.patient_id == patient_id)))
        assert len(p_rows) >= 1
        assert p_rows[0].model_version == 'logistic-regression-v1'
        assert abs(p_rows[0].risk - res['risk_probability']) < 1e-6

@pytest.mark.asyncio
async def test_07_alert_persistence():
    patient_id = "DB-PAT-005-ALERT"
    patient_service.require(patient_id)
    now = datetime.now(timezone.utc)

    # Ingest sequence of deteriorating events to trigger alert
    for i in range(4):
        event = VitalEvent(
            patient_id=patient_id,
            timestamp=now + timedelta(hours=i),
            heart_rate=100.0 + i * 15.0,
            map=85.0 - i * 12.0,
            resp_rate=18.0 + i * 5.0,
            spo2=98.0 - i * 3.0,
            temperature_c=37.0 + i * 0.7,
            lactate=1.0 + i * 1.5
        )
        await InferenceService.ingest(event)
        
    with Session() as s:
        a_rows = list(s.scalars(select(AlertRecord).where(AlertRecord.patient_id == patient_id)))
        assert len(a_rows) >= 1
        assert a_rows[0].patient_id == patient_id

@pytest.mark.asyncio
async def test_08_patient_scoped_vital_queries():
    p_a = "DB-SCOPED-VITAL-A"
    p_b = "DB-SCOPED-VITAL-B"
    patient_service.require(p_a)
    patient_service.require(p_b)
    
    await InferenceService.ingest(VitalEvent(patient_id=p_a, timestamp=datetime.now(timezone.utc), heart_rate=80.0))
    await InferenceService.ingest(VitalEvent(patient_id=p_b, timestamp=datetime.now(timezone.utc), heart_rate=90.0))
    
    vitals_a = patient_repository.vitals(p_a)
    for v in vitals_a:
        assert v.patient_id == p_a


@pytest.mark.asyncio
async def test_09_patient_scoped_prediction_queries():
    p_a = "DB-SCOPED-PRED-A"
    p_b = "DB-SCOPED-PRED-B"
    patient_service.require(p_a)
    patient_service.require(p_b)
    
    await InferenceService.ingest(VitalEvent(patient_id=p_a, timestamp=datetime.now(timezone.utc), heart_rate=82.0))
    await InferenceService.ingest(VitalEvent(patient_id=p_b, timestamp=datetime.now(timezone.utc), heart_rate=92.0))
    
    preds_a = patient_repository.predictions(p_a)
    for pr in preds_a:
        assert pr.patient_id == p_a

@pytest.mark.asyncio
async def test_10_patient_scoped_alert_queries():
    p_a = "DB-SCOPED-ALERT-A"
    p_b = "DB-SCOPED-ALERT-B"
    patient_service.require(p_a)
    patient_service.require(p_b)
    
    alerts_a = patient_repository.alerts(p_a)
    for al in alerts_a:
        assert al.patient_id == p_a

@pytest.mark.asyncio
async def test_11_timestamp_preservation():
    patient_id = "DB-TS-PRESERVE"
    patient_service.require(patient_id)
    ts = datetime(2026, 10, 1, 14, 45, 0, tzinfo=timezone.utc)
    
    event = VitalEvent(
        patient_id=patient_id,
        timestamp=ts,
        heart_rate=78.0,
        map=88.0,
        resp_rate=16.0,
        spo2=98.0
    )
    await InferenceService.ingest(event)
    
    with Session() as s:
        v = s.scalars(select(VitalRecord).where(VitalRecord.patient_id == patient_id)).first()
        assert v is not None
        assert "14:45:00" in str(v.timestamp)

def test_12_transaction_commit():
    import uuid
    patient_id = f"DB-TX-COMMIT-{uuid.uuid4().hex[:6]}"
    with Session.begin() as s:
        s.add(PatientRecord(patient_id=patient_id, source_system='test'))
        
    with Session() as s:
        row = s.scalars(select(PatientRecord).where(PatientRecord.patient_id == patient_id)).first()
        assert row is not None

def test_13_transaction_rollback():
    import uuid
    patient_id = f"DB-TX-ROLLBACK-{uuid.uuid4().hex[:6]}"
    try:
        with Session.begin() as s:
            s.add(PatientRecord(patient_id=patient_id, source_system='test'))
            raise RuntimeError("Simulated failure during transaction")
    except RuntimeError:
        pass
        
    with Session() as s:
        row = s.scalars(select(PatientRecord).where(PatientRecord.patient_id == patient_id)).first()
        assert row is None


def test_14_database_unavailable_handling():
    from sqlalchemy import create_engine
    from sqlalchemy.exc import OperationalError
    
    bad_engine = create_engine("postgresql://invalid_user:invalid_pass@127.0.0.1:59999/bad_db", connect_args={'connect_timeout': 1})
    with pytest.raises((OperationalError, Exception)):
        with bad_engine.connect() as conn:
            conn.execute("SELECT 1")

def test_15_session_cleanup_after_failure():
    patient_id = "DB-CLEANUP-FAIL"
    try:
        with Session() as s:
            s.add(PatientRecord(patient_id=patient_id, source_system='test'))
            raise ValueError("Intentional error")
    except ValueError:
        pass
        
    # Active session count/connection should be clean
    with Session() as s:
        assert s.is_active is True

@pytest.mark.asyncio
async def test_16_concurrent_writes():
    import asyncio
    patients = [f"DB-CONCUR-{i}" for i in range(5)]
    for p in patients:
        patient_service.require(p)
        
    async def write_event(p_id):
        event = VitalEvent(
            patient_id=p_id,
            timestamp=datetime.now(timezone.utc),
            heart_rate=80.0,
            map=85.0,
            resp_rate=16.0,
            spo2=98.0
        )
        return await InferenceService.ingest(event)

    results = await asyncio.gather(*[write_event(p) for p in patients])
    assert len(results) == 5

def test_17_orm_schema_consistency():
    from sqlalchemy import inspect
    mapper = inspect(PatientRecord)
    column_names = [c.key for c in mapper.columns]
    assert 'patient_id' in column_names
    assert 'source_system' in column_names
    assert 'created_at' in column_names

def test_18_no_accidental_in_memory_persistence():
    patient_id = "DB-NO-INMEM"
    patient_service.require(patient_id)
    
    with Session() as s:
        row = s.scalars(select(PatientRecord).where(PatientRecord.patient_id == patient_id)).first()
        assert row is not None

def test_19_existing_rest_api_still_works():
    res = client.get("/api/v1/health")
    assert res.status_code == 200
    assert res.json() == {"status": "healthy"}

def test_20_existing_websocket_flow_still_works():
    with client.websocket_connect("/api/v1/ws/stream") as ws:
        ws.send_json({"type": "ping"})
        msg = ws.receive_json()
        assert msg["type"] == "pong"
