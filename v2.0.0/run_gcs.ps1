# Guardia AI v2.0.0 — GCS Launcher
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  GUARDIA AI v2.0.0 -- Tactical Ground Control Station  " -ForegroundColor Cyan
Write-Host "  Pixhawk 2.4.8 + Bluetooth HC-05 + FlySky RC + Step GCS" -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    Write-Host "[ERROR] Virtual environment not found at .venv!" -ForegroundColor Red
    exit 1
}

Write-Host "[*] Starting Guardia AI GCS Server on http://localhost:8000..." -ForegroundColor Green
Write-Host "[*] Open your browser at http://localhost:8000" -ForegroundColor Yellow
Write-Host ""

& .venv\Scripts\python.exe -m uvicorn gcs.backend.main:app --host 0.0.0.0 --port 8000
