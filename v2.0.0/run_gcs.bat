@echo off
echo ========================================================
echo   GUARDIA AI v2.0.0 -- Tactical Ground Control Station
echo   Pixhawk 2.4.8 + Bluetooth HC-05 + FlySky RC + Step GCS
echo ========================================================
echo.

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [ERROR] Virtual environment not found at .venv!
    pause
    exit /b 1
)

echo [*] Starting Guardia AI GCS Server on http://localhost:8000...
echo [*] Press Ctrl+C to terminate.
echo.

.venv\Scripts\python.exe -m uvicorn gcs.backend.main:app --host 0.0.0.0 --port 8000
pause
