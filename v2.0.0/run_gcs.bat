@echo off
echo ========================================================
echo   GUARDIA AI v2.0.0 -- Tactical Ground Control Station
echo   Pixhawk 2.4.8 + ArduPilot Auto-Setup + Next.js GCS
echo ========================================================
echo.

cd /d "%~dp0"

echo [*] Launching GCS Backend on http://localhost:8000...
start "Guardia GCS Backend" /D "%~dp0" cmd /k ".venv\Scripts\python.exe -m uvicorn gcs.backend.main:app --host 0.0.0.0 --port 8000"

echo [*] Launching GCS Frontend on http://localhost:3000...
start "Guardia GCS Frontend" /D "%~dp0gcs\frontend" cmd /k "npm run dev"

timeout /t 3 /nobreak >nul
start http://localhost:3000
