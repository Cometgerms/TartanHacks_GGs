@echo off
REM Start backend and frontend servers for development

echo ========================================
echo Starting TartanHacks AI Dedalus
echo ========================================

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH
    pause
    exit /b 1
)

REM Check if Node.js is available
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js is not installed or not in PATH
    pause
    exit /b 1
)

echo.
echo Starting Backend (Flask on port 5000)...
echo ========================================

cd /d "%~dp0backend"
start "Backend - Flask" cmd /k "python AIDedalus\run_server.py"

echo.
echo Waiting 3 seconds for backend to start...
timeout /t 3 /nobreak >nul

echo.
echo Starting Frontend (Vite on port 5173)...
echo ========================================

cd /d "%~dp0frontend"
start "Frontend - Vite" cmd /k "npm run dev"

echo.
echo ========================================
echo Both servers are starting!
echo ========================================
echo.
echo Backend:  http://localhost:5000
echo Frontend: http://localhost:5173
echo.
echo Press any key to exit (servers will keep running)...
pause >nul

