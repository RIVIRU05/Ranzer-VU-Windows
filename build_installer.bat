@echo off
setlocal EnableDelayedExpansion
title Build RANZER Installer

:: ============================================================================
::  build_installer.bat
::  Builds RANZER_Setup_1.0.0.exe for end-user distribution.
::
::  Prerequisites (developer machine):
::    1. Inno Setup 6  — https://jrsoftware.org/isdl.php
::    2. Python 3.10+  — https://www.python.org/downloads/
::    3. PyInstaller   — pip install pyinstaller
::
::  Output:  build_output\installer\RANZER_Setup_1.0.0.exe
:: ============================================================================

echo.
echo ============================================================
echo  RANZER Installer Builder
echo ============================================================
echo.

:: ── Locate Inno Setup compiler ───────────────────────────────────────────────
set "ISCC="
for %%P in (
    "C:\Program Files (x86)\Inno Setup 6\ISCC.exe"
    "C:\Program Files\Inno Setup 6\ISCC.exe"
) do (
    if exist %%P set "ISCC=%%~P"
)

if not defined ISCC (
    echo [ERROR] Inno Setup 6 not found.
    echo         Download and install it from:
    echo           https://jrsoftware.org/isdl.php
    echo.
    pause
    exit /b 1
)
echo [OK] Inno Setup: %ISCC%

:: ── Step 1: Build PyInstaller exe ───────────────────────────────────────────
echo.
echo [1/3] Building ranzer.exe with PyInstaller...
call build_exe.bat nopause
if errorlevel 1 (
    echo [ERROR] build_exe.bat failed. See above for details.
    pause
    exit /b 1
)
echo [OK] PyInstaller build done.

:: ── Step 3: Compile installer ────────────────────────────────────────────────
echo.
echo [2/3] Compiling Inno Setup installer...
mkdir build_output\installer 2>nul
"%ISCC%" "packaging\windows\ranzer_setup.iss"
if errorlevel 1 (
    echo [ERROR] Inno Setup compilation failed.
    pause
    exit /b 1
)
echo [OK] Installer compiled.

:: ── Done ────────────────────────────────────────────────────────────────────
echo.
echo [3/3] Finished!
echo.
echo   Output:  build_output\installer\RANZER_Setup_1.0.0.exe
echo.
echo   Upload this file to a GitHub Release so users can download it.
echo.
pause
