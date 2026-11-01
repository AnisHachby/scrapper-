@echo off
echo ============================================
echo BVC Signal vs Noise - Product Launcher
echo ============================================
echo.

:: Check if services are already running
echo [1/4] Checking services...
curl -s http://localhost:8000/health >nul 2>&1
if %errorlevel% equ 0 (
    echo [OK] API Service already running on port 8000
) else (
    echo [!] API Service not running - start with: uvicorn src.dashboard_server:app --port 8000
)

echo.
echo [2/4] Running validation tests...
py src/tests/test_validation.py

echo.
echo [3/4] Running exactitude calculator...
py src/exactitude.py

echo.
echo [4/4] Starting dashboard server...
echo Open browser to: http://localhost:8000
echo Press Ctrl+C to stop
py -m uvicorn src.dashboard_server:app --port 8000 --reload
