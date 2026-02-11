@echo off
TITLE DayToDay - First Time Setup
echo ========================================
echo   DayToDay - First Time Setup
echo ========================================
echo.

set SCRIPT_DIR=%~dp0
set PROJECT_DIR=%SCRIPT_DIR%..
set BACKEND_DIR=%PROJECT_DIR%\backend
set FRONTEND_DIR=%PROJECT_DIR%\frontend
set VENV_DIR=%PROJECT_DIR%\venv
set CONFIG_DIR=%PROJECT_DIR%\config

REM Check Python
echo Checking Python...
python3 --version >nul 2>&1
if errorlevel 1 (
    py --version >nul 2>&1
    if errorlevel 1 (
        echo ERROR: Python 3.9+ is required but not found.
        echo Please install Python from https://www.python.org/downloads/
        pause
        exit /b 1
    )
    set PYTHON_CMD=py
) else (
    set PYTHON_CMD=python3
)
echo    Python found.

REM Check Node.js
echo Checking Node.js...
node --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Node.js 16+ is required but not found.
    echo Please install Node.js from https://nodejs.org/
    pause
    exit /b 1
)
echo    Node.js found.

REM Create virtual environment
echo.
echo [1/6] Creating virtual environment...
if not exist "%VENV_DIR%" (
    %PYTHON_CMD% -m venv "%VENV_DIR%"
    echo    Virtual environment created.
) else (
    echo    Virtual environment already exists.
)

REM Install Python dependencies
echo [2/6] Installing Python dependencies...
call "%VENV_DIR%\Scripts\activate.bat"
pip install -r "%BACKEND_DIR%\requirements.txt" -q
echo    Python dependencies installed.

REM Install Node.js dependencies
echo [3/6] Installing frontend dependencies...
cd /d "%FRONTEND_DIR%"
call npm install --silent 2>nul
echo    Frontend dependencies installed.

REM Build React frontend
echo [4/6] Building frontend...
call node node_modules\react-scripts\bin\react-scripts.js build
echo    Frontend built.

REM Setup config
echo [5/6] Setting up configuration...
if not exist "%CONFIG_DIR%\config.json" (
    if exist "%CONFIG_DIR%\config.template.json" (
        copy "%CONFIG_DIR%\config.template.json" "%CONFIG_DIR%\config.json" >nul
        echo    Config file created from template.
        echo.
        echo    OPTIONAL: Edit config\config.json to configure:
        echo      - word_doc_directories: Paths to scan for Word documents
        echo      - outlook_enabled: Enable/disable Outlook calendar collection
        echo      - onenote_enabled: Enable/disable OneNote collection
        echo.
    )
) else (
    echo    Config file already exists.
)

REM Run Django migrations
echo [6/6] Running database migrations...
cd /d "%BACKEND_DIR%"
python manage.py migrate --run-syncdb -q 2>nul
echo    Database ready.

echo.
echo ========================================
echo   Setup Complete!
echo ========================================
echo.
echo No Azure setup needed! DayToDay reads directly
echo from your local Outlook and OneNote.
echo.
echo Next steps:
echo   1. Make sure Outlook is open
echo   2. Run scripts\daytoday.bat to start the app
echo.
echo To build a standalone .exe:
echo   Run scripts\build_exe.bat
echo.
pause
