@echo off
REM =====================================================
REM  DayToDay - Build Executable
REM  Creates a distributable .exe package
REM =====================================================

echo.
echo ====================================================
echo  DayToDay - Building Executable
echo ====================================================
echo.

REM Navigate to project root
cd /d "%~dp0\.."
set PROJECT_ROOT=%cd%

REM Check venv exists
if not exist "venv\Scripts\python.exe" (
    echo ERROR: Virtual environment not found.
    echo Run setup.bat first.
    pause
    exit /b 1
)

REM Activate venv
call venv\Scripts\activate.bat

REM Step 1: Build React frontend
echo [1/3] Building React frontend...
cd frontend
call node node_modules\react-scripts\bin\react-scripts.js build
if %ERRORLEVEL% neq 0 (
    echo ERROR: React build failed.
    pause
    exit /b 1
)
cd ..
echo       React build complete.

REM Step 2: Run PyInstaller
echo [2/3] Running PyInstaller...
pyinstaller daytoday.spec --noconfirm --clean
if %ERRORLEVEL% neq 0 (
    echo ERROR: PyInstaller build failed.
    pause
    exit /b 1
)
echo       PyInstaller build complete.

REM Step 3: Copy config template to dist
echo [3/3] Finalizing distribution...
if not exist "dist\DayToDay\config" mkdir "dist\DayToDay\config"
copy "config\config.template.json" "dist\DayToDay\config\config.template.json" >nul

echo.
echo ====================================================
echo  BUILD COMPLETE!
echo ====================================================
echo.
echo  Distribution folder: %PROJECT_ROOT%\dist\DayToDay\
echo  Executable: %PROJECT_ROOT%\dist\DayToDay\DayToDay.exe
echo.
echo  To distribute: Copy the entire DayToDay folder
echo  to the target machine and run DayToDay.exe
echo.
pause
