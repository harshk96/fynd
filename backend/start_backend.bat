@echo off
echo ========================================
echo Starting Backend Server...
echo ========================================
cd /d "%~dp0"

REM Activate virtual environment if it exists
if exist "..\myfyndenv\Scripts\activate.bat" (
    echo Activating virtual environment...
    call "..\myfyndenv\Scripts\activate.bat"
) else (
    echo Warning: Virtual environment not found. Using system Python.
)

REM Check if requirements are installed
echo Checking dependencies...
python -c "import fastapi, uvicorn" 2>nul
if errorlevel 1 (
    echo Installing dependencies...
    pip install -r requirements.txt
)

REM Check if port 8000 is available
netstat -an | findstr ":8000" >nul
if not errorlevel 1 (
    echo WARNING: Port 8000 is already in use!
    echo Please close the application using port 8000 and try again.
    pause
    exit /b 1
)

echo.
echo Starting server on http://localhost:8000
echo Press Ctrl+C to stop the server
echo.
python main.py
pause

