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

REM Run the unified launcher (collects data + starts server + opens browser)
python "%PROJECT_DIR%\launcher.py"

echo.
echo DayToDay has been stopped.
pause
