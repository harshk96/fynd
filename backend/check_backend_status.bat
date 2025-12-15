@echo off
echo ========================================
echo Backend Server Status Check
echo ========================================
echo.

REM Check if port 8000 is in use
netstat -an | findstr ":8000" >nul
if errorlevel 1 (
    echo [X] Backend is NOT running on port 8000
    echo.
    echo To start the backend:
    echo 1. Run: start_backend.bat
    echo 2. Or manually: python main.py
    echo.
) else (
    echo [OK] Backend appears to be running on port 8000
    echo.
    echo Testing connection...
    curl -s http://localhost:8000 >nul 2>&1
    if errorlevel 1 (
        echo [X] Backend is not responding
        echo     Port 8000 is in use but server may not be accessible
    ) else (
        echo [OK] Backend is responding successfully!
        echo.
        echo You can access:
        echo - API: http://localhost:8000
        echo - Docs: http://localhost:8000/docs
    )
)

echo.
pause

