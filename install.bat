@echo off
:: =============================================================================
::  RANZER - Windows Installer
::  Must be run as Administrator.
::  Usage:  Right-click install.bat -> "Run as administrator"
:: =============================================================================
setlocal EnableDelayedExpansion

echo.
echo  ==========================================
echo       RANZER  Windows  Installer
echo  ==========================================
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
set "SOURCE=%~dp0ranzer"

:: ── Step 1: Build the EXE bundle ──────────────────────────────────────────────
echo Step 1/4 - Building EXE bundle...
echo.
call "%~dp0build_exe.bat" nopause
if errorlevel 1 (
    echo ERROR: Build failed.
    pause
    exit /b 1
)

:: ── Step 2: Copy to Program Files ─────────────────────────────────────────────
echo Step 2/4 - Installing to %INSTALL_DIR%...
:: Kill any running instance so Windows releases file locks
taskkill /F /IM ranzer.exe /T >nul 2>&1
taskkill /F /IM pythonw.exe /T >nul 2>&1
timeout /t 2 /nobreak >nul
if exist "%INSTALL_DIR%" (
    icacls "%INSTALL_DIR%" /reset /T /Q >nul 2>&1
    rmdir /s /q "%INSTALL_DIR%"
)
mkdir "%INSTALL_DIR%"
:: Copy PyInstaller bundle (ranzer.exe + _internal\ — used by CLI via PATH)
xcopy /E /I /Q "%BUNDLE%\*" "%INSTALL_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy bundle to %INSTALL_DIR%
    pause
    exit /b 1
)
:: Copy ranzer Python source package so the pythonw GUI launcher can import it
xcopy /E /I /Q "%SOURCE%\*" "%INSTALL_DIR%\ranzer\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy ranzer source package
    pause
    exit /b 1
)
echo       OK

:: ── Step 3: Create pythonw GUI launcher ───────────────────────────────────────
:: The frozen ranzer.exe has a Tcl/Tk bundling issue that blocks the GUI.
:: Instead we launch the GUI using the real Python interpreter (pythonw.exe),
:: which has working Tcl/Tk — same as "ranzer gui" from the command line.
echo Step 3/4 - Creating GUI launcher...

:: Find pythonw.exe via a temp script to avoid CMD quote-escaping hell
(
    echo import sys, os
    echo d = os.path.dirname(sys.executable^)
    echo pw = os.path.join(d, "pythonw.exe"^)
    echo print(pw if os.path.isfile(pw^) else sys.executable^)
) > "%TEMP%\ranzer_find_py.py"
for /f "delims=" %%P in ('python "%TEMP%\ranzer_find_py.py" 2^>nul') do set "PYTHONW=%%P"
del "%TEMP%\ranzer_find_py.py" >nul 2>&1

if "!PYTHONW!"=="" (
    echo ERROR: Could not locate Python. Is Python installed?
    pause
    exit /b 1
)
echo       Python launcher: !PYTHONW!

:: Generate launch_gui.vbs — sets PYTHONPATH to install dir so "ranzer"
:: package is importable, then runs pythonw silently (window style 0)
(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo Set env = WshShell.Environment^("Process"^)
    echo env^("PYTHONPATH"^) = "%INSTALL_DIR%"
    echo Dim pyExe
    echo pyExe = "!PYTHONW!"
    echo WshShell.Run Chr^(34^) ^& pyExe ^& Chr^(34^) ^& " -m ranzer gui", 0, False
) > "%INSTALL_DIR%\launch_gui.vbs"
echo       OK

:: ── Step 4: Start Menu shortcut + PATH ────────────────────────────────────────
echo Step 4/4 - Creating Start Menu shortcut...
set "SHORTCUT=%ProgramData%\Microsoft\Windows\Start Menu\Programs\RANZER.lnk"

:: Write shortcut via a temp PowerShell script to avoid CMD quoting issues
(
    echo $ws = New-Object -ComObject WScript.Shell
    echo $s  = $ws.CreateShortcut('!SHORTCUT!')
    echo $s.TargetPath       = 'C:\Windows\System32\wscript.exe'
    echo $s.Arguments        = '"!INSTALL_DIR!\launch_gui.vbs"'
    echo $s.WorkingDirectory = '!INSTALL_DIR!'
    echo $s.Description      = 'RANZER Ransomware Detection'
    echo $s.IconLocation     = '!INSTALL_DIR!\ranzer.exe,0'
    echo $s.Save()
) > "%TEMP%\ranzer_shortcut.ps1"
powershell -NoProfile -ExecutionPolicy Bypass -File "%TEMP%\ranzer_shortcut.ps1"
del "%TEMP%\ranzer_shortcut.ps1" >nul 2>&1
echo       OK

:: ── Add ranzer.exe to system PATH for CLI use ─────────────────────────────────
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYSPATH=%%B"
echo !SYSPATH! | findstr /i "%INSTALL_DIR%" >nul
if errorlevel 1 (
    setx /M PATH "!SYSPATH!;%INSTALL_DIR%" >nul
    echo       Added %INSTALL_DIR% to system PATH
)

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo  ==========================================
echo       RANZER installed successfully!
echo  ==========================================
echo.
echo   Launch via Start Menu: search "RANZER"
echo   Or from command line:  ranzer gui
echo.
echo   Uninstall: right-click uninstall.bat as Administrator
echo.
pause
