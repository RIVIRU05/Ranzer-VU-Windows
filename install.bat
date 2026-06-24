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
:: Copy PyInstaller bundle (ranzer.exe lives here but is NOT put in PATH)
xcopy /E /I /Q "%BUNDLE%\*" "%INSTALL_DIR%\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy bundle to %INSTALL_DIR%
    pause
    exit /b 1
)
:: Copy ranzer Python source package so the real-Python launchers can import it
xcopy /E /I /Q "%SOURCE%\*" "%INSTALL_DIR%\ranzer\" >nul
if errorlevel 1 (
    echo ERROR: Failed to copy ranzer source package
    pause
    exit /b 1
)
echo       OK

:: ── Step 3: Create launchers ───────────────────────────────────────────────────
:: The frozen ranzer.exe has a Tcl/Tk bundling issue that crashes the GUI.
:: We route every launch path through the real Python interpreter instead:
::   Start Menu  -> launch_gui.vbs  -> pythonw.exe (silent, no console)
::   "ranzer gui" in CMD -> ranzer.cmd -> pythonw.exe (detached, no console)
::   "ranzer ..." in CMD -> ranzer.cmd -> python.exe  (console output visible)
echo Step 3/4 - Creating launchers...

:: Find pythonw.exe — use a tiny temp script to avoid CMD quote-escaping hell
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
echo       Python launcher : !PYTHONW!

:: launch_gui.vbs — Start Menu entry; window style 0 = hidden (no console)
(
    echo Set WshShell = CreateObject^("WScript.Shell"^)
    echo Set env = WshShell.Environment^("Process"^)
    echo env^("PYTHONPATH"^) = "%INSTALL_DIR%"
    echo Dim pyExe
    echo pyExe = "!PYTHONW!"
    echo WshShell.Run Chr^(34^) ^& pyExe ^& Chr^(34^) ^& " -m ranzer gui", 0, False
) > "%INSTALL_DIR%\launch_gui.vbs"

:: ranzer.cmd in bin\ — what the user gets when typing "ranzer" in CMD.
:: bin\ is added to PATH instead of the root dir so .cmd is found before .exe.
:: "ranzer gui"  -> pythonw (detached, no console window)
:: "ranzer ..."  -> python  (console output shows in the terminal)
mkdir "%INSTALL_DIR%\bin"
(
    echo @echo off
    echo set "PYTHONPATH=%INSTALL_DIR%"
    echo if /i "%%1"=="gui" ^(
    echo     start "" "!PYTHONW!" -m ranzer %%*
    echo ^) else ^(
    echo     python -m ranzer %%*
    echo ^)
) > "%INSTALL_DIR%\bin\ranzer.cmd"
echo       OK

:: ── Step 4: Start Menu shortcut + PATH ────────────────────────────────────────
echo Step 4/4 - Creating Start Menu shortcut...
set "SHORTCUT=%ProgramData%\Microsoft\Windows\Start Menu\Programs\RANZER.lnk"

:: [char]34 = " — build Arguments string without any temp files
powershell -NoProfile -Command "$ws = New-Object -ComObject WScript.Shell; $s = $ws.CreateShortcut('!SHORTCUT!'); $s.TargetPath = 'C:\Windows\System32\wscript.exe'; $s.Arguments = [char]34 + '!INSTALL_DIR!\launch_gui.vbs' + [char]34; $s.WorkingDirectory = '!INSTALL_DIR!'; $s.Description = 'RANZER Ransomware Detection'; $s.IconLocation = '!INSTALL_DIR!\ranzer.exe,0'; $s.Save()"
echo       OK

:: ── Add bin\ to system PATH so ranzer.cmd is found (not ranzer.exe) ─────────
for /f "tokens=2*" %%A in ('reg query "HKLM\SYSTEM\CurrentControlSet\Control\Session Manager\Environment" /v Path 2^>nul') do set "SYSPATH=%%B"
echo !SYSPATH! | findstr /i "Ranzer\\bin" >nul
if errorlevel 1 (
    :: Also strip any old-style entry that lacks \bin, then append the new one
    set "NEWPATH=!SYSPATH:%INSTALL_DIR%;=!"
    setx /M PATH "!NEWPATH!;%INSTALL_DIR%\bin" >nul
    echo       Added %INSTALL_DIR%\bin to system PATH
)

:: ── Done ──────────────────────────────────────────────────────────────────────
echo.
echo  ==========================================
echo       RANZER installed successfully!
echo  ==========================================
echo.
echo   Launch via Start Menu  : search "RANZER"
echo   Launch from command line: ranzer gui
echo   (Open a new CMD window for PATH to take effect)
echo.
echo   Uninstall: right-click uninstall.bat as Administrator
echo.
pause
