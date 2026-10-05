# Guardia AI v2.0.0 — Unified GCS Launcher (Backend + Next.js Frontend)
param (
    [switch]$NoBrowser
)

Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "  GUARDIA AI v2.0.0 -- Tactical Ground Control Station  " -ForegroundColor Cyan
Write-Host "  Pixhawk 2.4.8 + ArduPilot Auto-Setup + Next.js GCS   " -ForegroundColor Cyan
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host ""

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

# Resolve Python Executable
$PythonExe = Join-Path $ScriptDir ".venv\Scripts\python.exe"
if (-not (Test-Path $PythonExe)) {
    $PythonExe = "python"
}

# 1. Clean up any stale node or uvicorn processes on ports 3000 / 8000
try {
    $staleConnections = Get-NetTCPConnection -LocalPort 8000, 3000 -ErrorAction SilentlyContinue
    if ($staleConnections) {
        Write-Host "[*] Freeing existing processes on ports 8000 and 3000..." -ForegroundColor DarkGray
        foreach ($conn in $staleConnections) {
            if ($conn.OwningProcess -gt 0) {
                Stop-Process -Id $conn.OwningProcess -Force -ErrorAction SilentlyContinue
            }
        }
        Start-Sleep -Milliseconds 600
    }
} catch {}

# 2. Launch Backend in dedicated window
Write-Host "[1/3] Starting Guardia AI GCS Backend on http://localhost:8000..." -ForegroundColor Green
Start-Process -FilePath "cmd.exe" -ArgumentList "/k title Guardia GCS Backend && `"$PythonExe`" -m uvicorn gcs.backend.main:app --host 0.0.0.0 --port 8000" -WorkingDirectory $ScriptDir

# 3. Launch Frontend in dedicated window
Write-Host "[2/3] Starting Next.js Tactical UI on http://localhost:3000..." -ForegroundColor Green
$FrontendDir = Join-Path $ScriptDir "gcs\frontend"
Start-Process -FilePath "cmd.exe" -ArgumentList "/k title Guardia GCS Frontend && npm run dev" -WorkingDirectory $FrontendDir

# 4. Summary & Browser Launch
Write-Host "[3/3] Systems Initialized!" -ForegroundColor Green
Write-Host "  -> Backend API & MAVLink Bridge: http://localhost:8000" -ForegroundColor Cyan
Write-Host "  -> Tactical Cockpit UI:          http://localhost:3000" -ForegroundColor Yellow
Write-Host ""
Write-Host "[*] Both Backend & Frontend running in separate console windows." -ForegroundColor Green
Write-Host "[*] Close their respective windows to stop each service." -ForegroundColor DarkGray
Write-Host ""

if (-not $NoBrowser) {
    Start-Sleep -Seconds 3
    Start-Process "http://localhost:3000"
}
