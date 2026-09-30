from fastapi.testclient import TestClient
from src.backend.main import app

client = TestClient(app)

def test_health_endpoint():
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy"}

def test_patient_api_flow():
    # 1. Create Patient
    create_res = client.post(
        "/api/v1/patients", 
        json={"name": "Integration Test", "age": 45, "medical_history": []},
        headers={"Authorization": "Bearer fake-super-secret-token"}
    )
    assert create_res.status_code == 200
    patient_id = create_res.json()["id"]
    
    # 2. Get Patient
    get_res = client.get(
        f"/api/v1/patients/{patient_id}",
        headers={"Authorization": "Bearer fake-super-secret-token"}
    )
    assert get_res.status_code == 200
    assert get_res.json()["name"] == "Integration Test"
    
    # 3. Get Risk
    risk_res = client.get(
        f"/api/v1/patients/{patient_id}/risk",
        headers={"Authorization": "Bearer fake-super-secret-token"}
    )
    assert risk_res.status_code == 200
    assert "risk_score" in risk_res.json()

def test_websocket_integration():
    with client.websocket_connect("/api/v1/ws") as websocket:
        websocket.send_text("Hello Server")
        data = websocket.receive_text()
        assert data == "Message text was: Hello Server"
