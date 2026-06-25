@echo off
:: =============================================================================
::  RANZER - Windows EXE Builder
::  Must be run on Windows with Python 3.10+ installed.
::  Usage:  build_exe.bat
:: =============================================================================
setlocal EnableDelayedExpansion

:: Always run from the folder this script lives in
cd /d "%~dp0"

echo.
echo  ==========================================
echo       RANZER  Windows  EXE  Builder
echo  ==========================================
echo.

:: ── Detect Python ─────────────────────────────────────────────────────────────
set "PYTHON="

python --version >nul 2>&1
if not errorlevel 1 set "PYTHON=python"

if "!PYTHON!"=="" (
    py --version >nul 2>&1
    if not errorlevel 1 set "PYTHON=py"
)

if "!PYTHON!"=="" (
    python3 --version >nul 2>&1
    if not errorlevel 1 set "PYTHON=python3"
)

if "!PYTHON!"=="" (
    echo ERROR: Python not found. Download from https://python.org
    echo        During install tick "Add Python to PATH" and "Install for all users".
    pause
    exit /b 1
)
echo [*] Using Python: !PYTHON!

:: ── Detect pip ────────────────────────────────────────────────────────────────
!PYTHON! -m pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip not found.
    pause
    exit /b 1
)

:: ── Step 1: Install dependencies ──────────────────────────────────────────────
echo [1/4] Installing dependencies...
!PYTHON! -m pip install --quiet watchdog psutil Pillow pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo       OK

:: ── Step 2: Create icon if none exists ────────────────────────────────────────
echo [2/4] Generating icon from logo.png...
del /f /q "packaging\windows\ranzer.ico" 2>nul
!PYTHON! packaging\windows\make_icon.py
if errorlevel 1 (
    echo       Icon generation failed - building without icon
    !PYTHON! -c "import re; spec=open('ranzer.spec').read(); spec=re.sub(r'icon=.*?,','',spec); open('ranzer.spec','w').write(spec)"
)

:: ── Step 3: PyInstaller bundle ────────────────────────────────────────────────
echo [3/4] Bundling with PyInstaller (may take 1-2 min)...
if exist "build_output" rmdir /s /q "build_output"
!PYTHON! -m PyInstaller ranzer.spec ^
    --distpath "build_output\dist" ^
    --workpath "build_output\work" ^
    --noconfirm ^
    --clean
if errorlevel 1 (
    echo ERROR: PyInstaller failed.
    pause
    exit /b 1
)
echo       OK - bundle: build_output\dist\ranzer\

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo [4/4] Build complete!
echo.
echo   Bundle : build_output\dist\ranzer\
echo   Run    : build_output\dist\ranzer\ranzer.exe gui
echo.
echo   To install system-wide, run:  install.bat
echo.
if "%~1"=="nopause" exit /b 0
pause