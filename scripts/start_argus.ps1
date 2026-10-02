# ARGUS Single-Command Startup Script for Local Development
# Runs Part 1 Simulator on port 8001 (DEMO_MODE=true) and Part 2 Backend on port 8000 with WS Bridge enabled.

$env:PYTHONPATH = "C:\Users\HP\Desktop\Argus\argus-sepsiswarner;C:\Users\HP\Desktop\Argus\argus-sepsiswarner\part1\backend"
$env:ARGUS_HOST = "0.0.0.0"
$env:ARGUS_PORT = "8001"
$env:ARGUS_DEMO_MODE = "true"
$env:ARGUS_DEMO_PATIENT_ID = "PATIENT-001"

$env:ARGUS_PART1_BRIDGE_ENABLED = "true"
$env:ARGUS_PART1_WS_URL = "ws://127.0.0.1:8001/api/v1/stream"

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "Starting ARGUS Data Source & Simulation Platform (Part 1 - Port 8001)..." -ForegroundColor Green
$part1Process = Start-Process python -ArgumentList "-m uvicorn app.main:app --host 0.0.0.0 --port 8001" -WorkingDirectory "C:\Users\HP\Desktop\Argus\argus-sepsiswarner\part1\backend" -PassThru -NoNewWindow

Start-Sleep -Seconds 3

Write-Host "Starting ARGUS Clinical Decision Support Backend (Part 2 - Port 8000)..." -ForegroundColor Green
$part2Process = Start-Process python -ArgumentList "-m uvicorn src.backend.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory "C:\Users\HP\Desktop\Argus\argus-sepsiswarner" -PassThru -NoNewWindow

Write-Host "==================================================" -ForegroundColor Cyan
Write-Host "ARGUS Services initialized:" -ForegroundColor Yellow
Write-Host "  - Part 1 Simulator: http://0.0.0.0:8001 (DEMO_MODE=true)" -ForegroundColor White
Write-Host "  - Part 2 Backend:   http://0.0.0.0:8000 (WS Bridge=Active)" -ForegroundColor White
Write-Host "  - Demo Patient:     PATIENT-001" -ForegroundColor White
Write-Host "==================================================" -ForegroundColor Cyan
