@echo off
:: ─────────────────────────────────────────────────────────────────────────────
::  RANZER — Windows EXE Builder
::  Must be run on Windows with Python 3.10+ installed.
::  Usage:  build_exe.bat
:: ─────────────────────────────────────────────────────────────────────────────
setlocal EnableDelayedExpansion

echo ╔══════════════════════════════════════════╗
echo ║     RANZER  Windows  EXE  Builder        ║
echo ╚══════════════════════════════════════════╝
echo.

:: ── Preflight ─────────────────────────────────────────────────────────────────
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found. Download from https://python.org
    pause
    exit /b 1
)

pip --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: pip not found.
    pause
    exit /b 1
)

:: ── Step 1: Install dependencies ──────────────────────────────────────────────
echo [1/4] Installing dependencies...
pip install --quiet watchdog psutil Pillow pyinstaller
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    pause
    exit /b 1
)
echo       OK

:: ── Step 2: Create a placeholder icon if none exists ──────────────────────────
if not exist "packaging\windows\ranzer.ico" (
    echo [2/4] Generating icon from logo.png...
    python -c "
from PIL import Image
import os
os.makedirs('packaging\\\\windows', exist_ok=True)
img = Image.open('ranzer\\\\gui\\\\logo.png').convert('RGBA')
sizes = [(16,16),(32,32),(48,48),(64,64),(128,128),(256,256)]
imgs = [img.resize(s) for s in sizes]
imgs[0].save('packaging\\\\windows\\\\ranzer.ico', format='ICO', sizes=sizes, append_images=imgs[1:])
print('Icon saved.')
" 2>nul || (
        echo       Icon generation skipped ^(Pillow issue^) — building without icon
        :: Remove icon line from spec so build doesn't fail
        python -c "
import re
spec = open('ranzer.spec').read()
spec = re.sub(r\",\s*icon=.*\", '', spec)
open('ranzer.spec','w').write(spec)
"
    )
) else (
    echo [2/4] Icon already exists — skipping.
)

:: ── Step 3: PyInstaller bundle ────────────────────────────────────────────────
echo [3/4] Bundling app with PyInstaller ^(may take 1-2 min^)...
if exist "build_output" rmdir /s /q "build_output"
pyinstaller ranzer.spec ^
    --distpath "build_output\dist" ^
    --workpath "build_output\work" ^
    --noconfirm ^
    --clean
if errorlevel 1 (
    echo ERROR: PyInstaller failed.
    pause
    exit /b 1
)
echo       OK — bundle: build_output\dist\ranzer\

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo [4/4] Build complete!
echo.
echo   Bundle : build_output\dist\ranzer\
echo   Run    : build_output\dist\ranzer\ranzer.exe gui
echo.
echo   To install system-wide, run:  install.bat
echo.
pause
