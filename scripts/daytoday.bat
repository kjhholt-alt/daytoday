@echo off
TITLE DayToDay - Daily Summary App
echo ========================================
echo   DayToDay - Your Daily Summary Tool
echo ========================================
echo.

REM Determine directories
set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set BACKEND_DIR=%PROJECT_DIR%\backend
set FRONTEND_DIR=%PROJECT_DIR%\frontend
set VENV_DIR=%PROJECT_DIR%\venv

REM Check virtual environment exists
if not exist "%VENV_DIR%\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found at %VENV_DIR%
    echo Please run setup.bat first.
    pause
    exit /b 1
)

REM Activate virtual environment
call "%VENV_DIR%\Scripts\activate.bat"

REM Run data collection
echo.
echo [1/3] Collecting today's data from Outlook, Teams, OneNote...
echo.
python "%BACKEND_DIR%\manage.py" collect_today
if errorlevel 1 (
    echo.
    echo WARNING: Data collection encountered errors. Check the app for details.
    echo.
)

REM Start Django backend if not already running
echo [2/3] Starting backend server...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":8000.*LISTEN" 2^>nul') do set BACKEND_PID=%%a
if not defined BACKEND_PID (
    start "DayToDay-Backend" /MIN cmd /c "cd /d "%BACKEND_DIR%" && python manage.py runserver 8000 --noreload"
    timeout /t 3 /nobreak >nul
    echo    Backend started on http://localhost:8000
) else (
    echo    Backend already running.
)

REM Start React frontend if not already running
echo [3/3] Starting frontend...
for /f "tokens=5" %%a in ('netstat -aon ^| findstr ":3000.*LISTEN" 2^>nul') do set FRONTEND_PID=%%a
if not defined FRONTEND_PID (
    start "DayToDay-Frontend" /MIN cmd /c "cd /d "%FRONTEND_DIR%" && npm start"
    timeout /t 8 /nobreak >nul
    echo    Frontend started on http://localhost:3000
) else (
    echo    Frontend already running.
)

REM Open browser
echo.
echo Opening DayToDay in your browser...
start http://localhost:3000
echo.
echo ========================================
echo   DayToDay is running!
echo   - Backend:  http://localhost:8000
echo   - Frontend: http://localhost:3000
echo ========================================
echo.
echo Close this window when you're done.
pause
