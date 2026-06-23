@echo off
:: RANZER — Windows Uninstaller
:: Must be run as Administrator.
setlocal EnableDelayedExpansion

net session >nul 2>&1
if errorlevel 1 (
    echo ERROR: Must be run as Administrator.
    pause
    exit /b 1
)

set "INSTALL_DIR=C:\Program Files\Ranzer"
set "SHORTCUT=%ProgramData%\Microsoft\Windows\Start Menu\Programs\RANZER.lnk"

echo Removing RANZER...

:: Kill any running instance so Windows releases the file locks
taskkill /F /IM ranzer.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul

:: Remove self-protection ACLs first (required before deletion)
icacls "%INSTALL_DIR%" /reset /T /Q >nul 2>&1

:: Remove files
if exist "%INSTALL_DIR%" rmdir /s /q "%INSTALL_DIR%"
if exist "%SHORTCUT%"    del /f /q "%SHORTCUT%"

:: Remove from PATH
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYSPATH=%%B"
set "NEWPATH=!SYSPATH:%INSTALL_DIR%;=!"
setx /M PATH "!NEWPATH!" >nul 2>&1

echo RANZER uninstalled.
pause
