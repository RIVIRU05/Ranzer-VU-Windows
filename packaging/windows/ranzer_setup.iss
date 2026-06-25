; =============================================================================
;  RANZER — Inno Setup Installer Script
;  Produces:  RANZER_Setup_1.0.0.exe
;  Requires:  Inno Setup 6.x  (https://jrsoftware.org/isdl.php)
;             PyInstaller bundle already built by build_exe.bat
; =============================================================================

#define AppName      "RANZER"
#define AppVersion   "1.0.0"
#define AppPublisher "RANZER Team"
#define AppURL       "https://ranzer.io"
#define AppDesc      "Ransomware Detection & Endpoint Protection"
#define InstallDir   "{autopf}\Ranzer"

[Setup]
AppId={{A3F82C10-6B7D-4E2A-9F1D-C5B830D47E82}}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher={#AppPublisher}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={#InstallDir}
DefaultGroupName={#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=admin
OutputDir=..\..\build_output\installer
OutputBaseFilename=RANZER_Setup_{#AppVersion}
SetupIconFile=ranzer.ico
WizardStyle=modern
WizardSizePercent=120
Compression=lzma2/ultra64
SolidCompression=yes
UninstallDisplayIcon={app}\ranzer.exe
UninstallDisplayName={#AppName} {#AppVersion}
MinVersion=10.0
VersionInfoVersion={#AppVersion}
VersionInfoDescription={#AppDesc}
VersionInfoCompany={#AppPublisher}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; \
    Description: "Create a &Desktop shortcut"; \
    GroupDescription: "Additional shortcuts:"; \
    Flags: unchecked

[Dirs]
Name: "{app}\bin"
Name: "{app}\ranzer"

[Files]
; ── PyInstaller bundle (ranzer.exe + _internal\) ──────────────────────────────
Source: "..\..\build_output\dist\ranzer\*"; \
    DestDir: "{app}"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; ── Python source package (imported by pythonw GUI launcher) ──────────────────
Source: "..\..\ranzer\*"; \
    DestDir: "{app}\ranzer"; \
    Flags: ignoreversion recursesubdirs createallsubdirs

; ── App icon (used directly by shortcuts) ─────────────────────────────────────
Source: "ranzer.ico"; \
    DestDir: "{app}"; \
    Flags: ignoreversion

; ── Inno Setup will call [Code] to generate launch_gui.vbs + bin\ranzer.cmd ──

[Icons]
; Start Menu
Name: "{group}\{#AppName}"; \
    Filename: "{sys}\wscript.exe"; \
    Parameters: """{app}\launch_gui.vbs"""; \
    IconFilename: "{app}\ranzer.ico"; \
    Comment: "{#AppDesc}"

Name: "{group}\{#AppName} (CLI Help)"; \
    Filename: "{sys}\cmd.exe"; \
    Parameters: "/k ranzer --help"; \
    Comment: "Open a terminal with RANZER CLI"

Name: "{group}\Uninstall {#AppName}"; \
    Filename: "{uninstallexe}"

; Desktop (optional task)
Name: "{commondesktop}\{#AppName}"; \
    Filename: "{sys}\wscript.exe"; \
    Parameters: """{app}\launch_gui.vbs"""; \
    IconFilename: "{app}\ranzer.ico"; \
    Comment: "{#AppDesc}"; \
    Tasks: desktopicon

[Registry]
; Add {app}\bin to system PATH so "ranzer" works from any terminal
Root: HKLM; \
    Subkey: "SYSTEM\CurrentControlSet\Control\Session Manager\Environment"; \
    ValueType: expandsz; ValueName: "Path"; \
    ValueData: "{olddata};{app}\bin"; \
    Check: NeedsAddPath(ExpandConstant('{app}\bin'))

[Run]
; Refresh Windows icon cache so the RANZER icon appears correctly for all users
Filename: "{sys}\ie4uinit.exe"; Parameters: "-ClearIconCache"; \
    Flags: runhidden waituntilterminated; \
    StatusMsg: "Refreshing icon cache..."
Filename: "{sys}\ie4uinit.exe"; Parameters: "-show"; \
    Flags: runhidden waituntilterminated

[UninstallDelete]
; Clean up generated files not tracked by the installer
Type: files;       Name: "{app}\launch_gui.vbs"
Type: files;       Name: "{app}\bin\ranzer.cmd"
Type: dirifempty;  Name: "{app}\bin"

[Code]
// ── Python detection ─────────────────────────────────────────────────────────

// Versions to search for, newest first
var
  PythonExe: String;
  PythonWExe: String;

function FindPython(): Boolean;
var
  i: Integer;
  Versions: TArrayOfString;
  Key, ExePath, Dir: String;
begin
  Result := False;

  // ── 1. Try standard registry locations (python.org installer) ──────────────
  SetArrayLength(Versions, 8);
  Versions[0] := '3.14'; Versions[1] := '3.13';
  Versions[2] := '3.12'; Versions[3] := '3.11';
  Versions[4] := '3.10'; Versions[5] := '3.9';
  Versions[6] := '3.8';  Versions[7] := '3.7';

  for i := 0 to GetArrayLength(Versions) - 1 do
  begin
    Key := 'SOFTWARE\Python\PythonCore\' + Versions[i] + '\InstallPath';
    if RegQueryStringValue(HKLM, Key, 'ExecutablePath', ExePath) or
       RegQueryStringValue(HKCU, Key, 'ExecutablePath', ExePath) or
       RegQueryStringValue(HKLM, Key, '', ExePath) or
       RegQueryStringValue(HKCU, Key, '', ExePath) then
    begin
      if ExePath <> '' then
      begin
        // Value may be the directory or the exe itself
        if LowerCase(ExtractFileExt(ExePath)) = '.exe' then
          Dir := ExtractFileDir(ExePath)
        else
          Dir := ExePath;
        PythonExe  := AddBackslash(Dir) + 'python.exe';
        PythonWExe := AddBackslash(Dir) + 'pythonw.exe';
        if FileExists(PythonExe) then
        begin
          if not FileExists(PythonWExe) then PythonWExe := PythonExe;
          Result := True;
          Exit;
        end;
      end;
    end;
  end;

  // ── 2. Fall back to PATH search (handles winget, Store, per-user installs) ─
  ExePath := FileSearch('python.exe', GetEnv('PATH'));
  if ExePath <> '' then
  begin
    Dir := ExtractFileDir(ExePath);
    PythonExe  := ExePath;
    PythonWExe := AddBackslash(Dir) + 'pythonw.exe';
    if not FileExists(PythonWExe) then PythonWExe := PythonExe;
    Result := True;
    Exit;
  end;
end;

// ── PATH helper ──────────────────────────────────────────────────────────────

function NeedsAddPath(NewPath: String): Boolean;
var
  OldPath: String;
begin
  if not RegQueryStringValue(
      HKLM,
      'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
      'Path', OldPath) then
  begin
    Result := True;
    Exit;
  end;
  Result := Pos(';' + Uppercase(NewPath) + ';',
                ';' + Uppercase(OldPath) + ';') = 0;
end;

// ── File generators ──────────────────────────────────────────────────────────

procedure GenerateLaunchVBS();
var
  InstDir: String;
  Lines: TArrayOfString;
begin
  InstDir := ExpandConstant('{app}');
  SetArrayLength(Lines, 6);
  Lines[0] := 'Set WshShell = CreateObject("WScript.Shell")';
  Lines[1] := 'Set env = WshShell.Environment("Process")';
  Lines[2] := 'env("PYTHONPATH") = "' + InstDir + '"';
  Lines[3] := 'Dim pyExe';
  Lines[4] := 'pyExe = "' + PythonWExe + '"';
  Lines[5] := 'WshShell.Run Chr(34) & pyExe & Chr(34) & " -m ranzer gui", 0, False';
  SaveStringsToFile(InstDir + '\launch_gui.vbs', Lines, False);
end;

procedure GenerateCmdWrapper();
var
  InstDir: String;
  Lines: TArrayOfString;
begin
  InstDir := ExpandConstant('{app}');
  SetArrayLength(Lines, 7);
  Lines[0] := '@echo off';
  Lines[1] := 'set "PYTHONPATH=' + InstDir + '"';
  Lines[2] := 'if /i "%1"=="gui" (';
  Lines[3] := '    start "" "' + PythonWExe + '" -m ranzer %*';
  Lines[4] := ') else (';
  Lines[5] := '    python -m ranzer %*';
  Lines[6] := ')';
  ForceDirectories(InstDir + '\bin');
  SaveStringsToFile(InstDir + '\bin\ranzer.cmd', Lines, False);
end;

// ── Wizard event hooks ───────────────────────────────────────────────────────

function InitializeSetup(): Boolean;
begin
  Result := True;
  if not FindPython() then
  begin
    MsgBox(
      'RANZER requires Python 3.10 or later, which was not found on this system.' + #13#10 + #13#10 +
      'Please download and install Python from:' + #13#10 +
      '  https://www.python.org/downloads/' + #13#10 + #13#10 +
      'During installation, make sure to tick:' + #13#10 +
      '  "Add Python to PATH"' + #13#10 + #13#10 +
      'Then re-run this installer.',
      mbCriticalError, MB_OK);
    Result := False;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Generate the two launcher files using the pythonw path we found
    GenerateLaunchVBS();
    GenerateCmdWrapper();

    // Install pip packages silently
    Exec(PythonExe,
         '-m pip install --quiet --upgrade watchdog psutil Pillow',
         '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  OldPath, NewPath: String;
  BinDir: String;
begin
  if CurUninstallStep = usPostUninstall then
  begin
    // Remove {app}\bin from system PATH
    BinDir := ExpandConstant('{app}\bin');
    if RegQueryStringValue(
        HKLM,
        'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
        'Path', OldPath) then
    begin
      NewPath := OldPath;
      StringChangeEx(NewPath, ';' + BinDir, '', True);
      StringChangeEx(NewPath, BinDir + ';', '', True);
      RegWriteStringValue(
        HKLM,
        'SYSTEM\CurrentControlSet\Control\Session Manager\Environment',
        'Path', NewPath);
    end;
  end;
end;
