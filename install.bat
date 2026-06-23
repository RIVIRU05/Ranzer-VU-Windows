@echo off
:: ─────────────────────────────────────────────────────────────────────────────
::  RANZER — Windows Installer
::  Must be run as Administrator.
::  Usage:  Right-click install.bat → "Run as administrator"
:: ─────────────────────────────────────────────────────────────────────────────
setlocal EnableDelayedExpansion

echo ╔══════════════════════════════════════════╗
echo ║          RANZER  Windows  Installer      ║
echo ╚══════════════════════════════════════════╝
echo.

:: ── Check admin privileges ────────────────────────────────────────────────────
net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: This installer must be run as Administrator.
    echo Right-click install.bat and choose "Run as administrator".
    pause
    exit /b 1
)

set "INSTALL_DIR=C:\Program Files\Ranzer"
set "BUNDLE=%~dp0build_output\dist\ranzer"

:: ── Step 1: Build the EXE bundle ──────────────────────────────────────────────
echo Step 1/4 — Building EXE bundle...
echo.
call "%~dp0build_exe.bat" nopause
if errorlevel 1 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)

:: ── Step 2: Copy to Program Files ─────────────────────────────────────────────
echo Step 2/4 — Installing to %INSTALL_DIR%...
if exist "%INSTALL_DIR%" (
    :: Remove immutable ACL before overwriting
    icacls "%INSTALL_DIR%" /reset /T /Q >nul 2>&1
    rmdir /s /q "%INSTALL_DIR%"
)
mkdir "%INSTALL_DIR%"
xcopy /E /I /Q "%BUNDLE%\*" "%INSTALL_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy files to %INSTALL_DIR%
    pause
    exit /b 1
)
echo       OK

:: ── Step 3: Self-protection via ACLs ──────────────────────────────────────────
echo Step 3/4 — Applying self-protection...
:: Grant full control to SYSTEM and Administrators only.
:: Deny write/delete to all other users — ransomware running as a normal user
:: cannot modify or delete Ranzer's own files.
icacls "%INSTALL_DIR%" /inheritance:r /T /Q >nul
icacls "%INSTALL_DIR%" /grant:r "SYSTEM:(OI)(CI)F" /T /Q >nul
icacls "%INSTALL_DIR%" /grant:r "Administrators:(OI)(CI)F" /T /Q >nul
icacls "%INSTALL_DIR%" /deny "Everyone:(D,WDAC,WO)" /T /Q >nul
echo       OK

:: ── Step 4: Start Menu shortcut ───────────────────────────────────────────────
echo Step 4/4 — Creating Start Menu shortcut...
set "SHORTCUT=%ProgramData%\Microsoft\Windows\Start Menu\Programs\RANZER.lnk"
powershell -NoProfile -Command ^
    "$ws = New-Object -ComObject WScript.Shell; ^
     $s = $ws.CreateShortcut('%SHORTCUT%'); ^
     $s.TargetPath = '%INSTALL_DIR%\ranzer.exe'; ^
     $s.Arguments = 'gui'; ^
     $s.WorkingDirectory = '%INSTALL_DIR%'; ^
     $s.Description = 'RANZER Ransomware Detection'; ^
     $s.IconLocation = '%INSTALL_DIR%\ranzer.exe,0'; ^
     $s.Save()"
echo       OK

:: ── Add ranzer to system PATH ─────────────────────────────────────────────────
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYSPATH=%%B"
echo !SYSPATH! | findstr /i "%INSTALL_DIR%" >nul
if errorlevel 1 (
    setx /M PATH "!SYSPATH!;%INSTALL_DIR%" >nul
    echo       Added %INSTALL_DIR% to system PATH
)

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo ╔══════════════════════════════════════════╗
echo ║   RANZER installed successfully!         ║
echo ╚══════════════════════════════════════════╝
echo.
echo   Launch via Start Menu: search "RANZER"
echo   Or from command line:  ranzer gui
echo.
echo   Uninstall:
echo     1. Run uninstall.bat as Administrator
echo     2. Or: icacls "C:\Program Files\Ranzer" /reset /T
echo            rmdir /s /q "C:\Program Files\Ranzer"
echo.
pause
