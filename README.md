# RANZER - Ransomware Analyzer & Endpoint Protection System (Windows)

> Capstone Project | Group C | Victoria University

RANZER is a lightweight, real-time, signature-free **Endpoint Protection System (EPS)** that detects ransomware by monitoring the **act of encryption** - not known malware signatures. It combines Shannon entropy analysis, honey file deception, and process behaviour tracking into a unified hybrid detection engine.

This is the **Windows port**. For the Linux version see the [Ranzer repository](https://github.com/RIVIRU05/Ranzer).

---

## How It Works

```
File Modified / Created
        │
        ▼
  File Watcher (watchdog)
        │
    ┌───┴─────────────────────┐
    ▼                         ▼
Entropy Monitor         Honey File Engine
(Shannon entropy)       (decoy file traps)
    │                         │
    └──────────┬──────────────┘
               ▼
      Process Behaviour Tracker
      (psutil.io_counters - who did this?)
               ▼
      Threat Correlator
      (decay-weighted multi-signal scoring)
               ▼
      Alert Handler
      (log + notify + GUI + export)
```

Instead of relying on known malware signatures, RANZER watches **what files are doing**:

- **Entropy spike** on a modified file → file may be getting encrypted
- **Honey file touched** → ransomware walked into a decoy trap
- **Process writing 100 KB/s+ to monitored directories** → mass encryption behaviour
- **Same PID triggers multiple engines** → cross-signal score bonus, action recommended

---

## Project Structure

```
Ranzer-Windows/
├── ranzer/
│   ├── __init__.py
│   ├── __main__.py               ← python -m ranzer entry point
│   ├── cli.py                    ← Command line interface (Windows paths)
│   ├── core/
│   │   ├── engine.py             ← Main orchestrator (RanzerEngine + RanzerConfig)
│   │   ├── entropy_monitor.py    ← Shannon entropy analysis
│   │   ├── honey_file_engine.py  ← Decoy file deployment & detection
│   │   ├── process_tracker.py    ← Process I/O via psutil.io_counters (Windows)
│   │   ├── threat_correlator.py  ← Multi-signal threat scoring
│   │   ├── alert_handler.py      ← Logging, notifications, export
│   │   └── file_watcher.py       ← Real-time filesystem listener (Windows)
│   └── gui/
│       ├── app.py                ← GUI entry point
│       ├── landing.py            ← Welcome / mode selection screen
│       ├── main_window.py        ← Main application window
│       ├── setup_window.py       ← Directory & config setup
│       ├── theme.py              ← Colours, fonts, logo loader
│       └── views/
│           ├── dashboard.py      ← Live stats & alert preview
│           ├── alerts.py         ← Full alert table + search + export
│           ├── actions.py        ← Detected processes & manual termination
│           └── home.py
├── packaging/
│   └── windows/
│       └── ranzer.ico            ← App icon (auto-generated on first build)
├── ranzer.spec                   ← PyInstaller bundle spec (Windows)
├── build_exe.bat                 ← Builds the .exe bundle via PyInstaller
├── install.bat                   ← Installs to Program Files + self-protection
├── uninstall.bat                 ← Cleanly removes RANZER
├── simulate_ransomware.py        ← High-entropy file simulation (safe testing)
├── simulate_risk_low.py          ← High write-rate, low entropy simulation
└── requirements.txt
```

---

## Requirements

- **OS:** Windows 10 / 11 (64-bit)
- **Python:** 3.10+ - download from [python.org](https://www.python.org/downloads/)
- **Dependencies:** `watchdog`, `psutil`, `Pillow` (installed automatically)
- **Admin rights:** Required for install only (not for running from source)

---

## Installation

### Option A - Install system-wide (recommended)

```
git clone https://github.com/RIVIRU05/Ranzer-Windows.git
cd Ranzer-Windows
```

Right-click `install.bat` → **Run as administrator**

That's it. The script builds the `.exe` bundle, copies it to `C:\Program Files\Ranzer\`, creates a Start Menu shortcut, and applies self-protection.

Launch from the **Start Menu** (search "RANZER"), or from any command prompt:

```
ranzer gui
```

Uninstall:

Right-click `uninstall.bat` → **Run as administrator**

---

### Option B - Run from source (development)

```bat
git clone https://github.com/RIVIRU05/Ranzer-Windows.git
cd Ranzer-Windows

python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

:: GUI
python -m ranzer gui

:: CLI
python -m ranzer start --dirs C:\Users\you\Documents
```

---

## CLI Reference

```bat
:: Launch GUI
ranzer gui

:: Start monitoring (comma-separated directories)
ranzer start --dirs C:\Users\you\Documents,C:\Users\you\Desktop

:: Start with custom entropy threshold (default 7.5, range 6.0–8.0)
ranzer start --dirs C:\Users\you\Documents --threshold 7.2

:: Start with auto-terminate enabled
ranzer start --dirs C:\Users\you\Documents --auto-terminate

:: Start without honey files
ranzer start --dirs C:\Users\you\Documents --no-honeyfiles

:: Check if RANZER is running
ranzer status

:: View last 20 alerts
ranzer log

:: View only HIGH and CRITICAL alerts
ranzer log --severity HIGH

:: Scan a single file for entropy
ranzer scan --file C:\path\to\suspicious.bin

:: Export alerts
ranzer export --format json --output alerts.json
ranzer export --format csv  --output alerts.csv
ranzer export --format txt  --output alerts.txt
```

---

## Self-Protection

When installed via `install.bat`, RANZER applies **Windows ACL restrictions** to `C:\Program Files\Ranzer\`:

```
SYSTEM        - Full Control
Administrators - Full Control
Everyone      - Deny: Delete, Write DAC, Write Owner
```

This means:

- **User-space ransomware** (running as a normal user or even a non-admin process) cannot modify, rename, or delete any RANZER file.
- The files are only removable by an Administrator explicitly running `uninstall.bat`, which resets the ACLs before deletion.
- This is the Windows equivalent of Linux's `chattr +i` immutable flag used in the Linux version.

---

## GUI Overview

| View | What it shows |
|---|---|
| **Dashboard** | Live threat score, alert counts, last 5 events |
| **Alerts** | Full alert log with search, severity filter, and export |
| **System Actions** | Detected malicious processes with live CPU/status and manual terminate |

Threat popups appear automatically:
- **HIGH** - bottom-right corner notification, auto-dismisses after 12 s
- **CRITICAL** - centred modal, requires manual dismissal

---

## Detection Engines

### 1. Entropy Monitor
Calculates Shannon entropy (0–8 bits/byte) on every file write. Encrypted or compressed data scores near 8.0. Skips known high-entropy formats (`.zip`, `.jpg`, `.mp4`, etc.) to avoid false positives. Threshold default: **7.5**.

### 2. Honey File Engine
Deploys realistic decoy files (`credentials.txt`, `financial_report_2024.docx`, `passwords_backup.txt`, etc.) into monitored directories. Any modification, deletion, or rename fires an immediate HIGH/CRITICAL alert.

### 3. Process Behaviour Tracker
Uses `psutil.io_counters().write_bytes` (sampled every 0.5 s) to measure write volume for every running process. Flags processes sustaining **100 KB/s+** write rates to monitored directories. Maintains a large whitelist of Windows processes (`explorer.exe`, `svchost.exe`, `winword.exe`, browsers, system daemons) to prevent false positives.

### 4. File Watcher
Watchdog-based real-time event listener. Counts **new file creations** per directory per 5-second window. Ten or more new files in 5 s triggers a rapid-write PID scan using `psutil.open_files()`. Entropy checks run on every file modification.

### 5. Threat Correlator
Combines signals from all engines into a decay-weighted score. Signals lose weight over a 30 s window. A PID appearing in multiple engine types gets a cross-signal bonus. Thresholds:

| Level | Score | Action |
|---|---|---|
| LOW | 20–39 | MONITOR |
| MEDIUM | 40–64 | ALERT |
| HIGH | 65–89 | ALERT + popup |
| CRITICAL | 90+ | TERMINATE (if auto-terminate enabled) |

### 6. Alert Handler
Routes all events to:
- Dated log file: `logs\ranzer_events_YYYY-MM-DD.log`
- GUI event queue (GUI mode)
- In-memory ring buffer (last 500 events, exportable)

---

## Log Files

| File | Contents |
|---|---|
| `logs\ranzer_YYYY-MM-DD.log` | Full engine log - startup, scans, debug |
| `logs\ranzer_events_YYYY-MM-DD.log` | Detection events - one JSON object per line |
| `.ranzer_honey_state.json` | Honey file registry (auto-created on start) |

```bat
:: Watch alerts appear live (PowerShell)
Get-Content logs\ranzer_events_latest.log -Wait

:: Pretty-print the last alert
python -c "import json,sys; [print(json.dumps(json.loads(l),indent=2)) for l in open('logs/ranzer_events_latest.log')]" 2>nul
```

---

## Testing (Safe Simulation)

> Never test with real ransomware outside an isolated VM.

```bat
:: Trigger entropy detection - writes a random (high-entropy) file
python simulate_ransomware.py

:: Trigger low-risk / write-rate detection only
python simulate_risk_low.py

:: Manually trigger a honey file alert
echo TAMPERED >> C:\Users\you\Desktop\ranzer_test\credentials.txt

:: One-shot entropy scan of any file
ranzer scan --file C:\path\to\file.bin
```

---

## Differences from the Linux Version

| Feature | Linux | Windows |
|---|---|---|
| Write I/O tracking | `/proc/[pid]/io` wchar | `psutil.io_counters().write_bytes` |
| Open file detection | `/proc/[pid]/fd` scan | `psutil.open_files()` |
| Process CWD / cmdline | `/proc/[pid]/cwd`, `/proc/[pid]/cmdline` | `psutil.cwd()`, `psutil.cmdline()` |
| Temp files | `/tmp/ranzer.pid` | `%TEMP%\ranzer.pid` |
| Self-protection | `chattr +i` immutable flag | `icacls` ACL deny rules |
| Packaging | `.deb` + `install.sh` | `.exe` bundle + `install.bat` |
| Desktop integration | `.desktop` file | Start Menu `.lnk` shortcut |

---

## Roadmap

- [x] Core detection engines (entropy, honey files, process I/O, threat correlator)
- [x] CLI interface (`start`, `status`, `log`, `scan`, `export`, `gui`)
- [x] Tkinter GUI (Dashboard, Alerts, System Actions, threat popups)
- [x] Windows-native process I/O tracking via psutil
- [x] `.exe` bundle + `install.bat` single-command installer
- [x] Self-protection via Windows ACLs (`icacls`)
- [x] Start Menu shortcut + PATH registration
- [ ] Windows toast notifications (replace GUI-only alerts)
- [ ] Remote admin mode (monitor machines over network)
- [ ] Email / SMS alert integration
- [ ] Scheduled scan reports

---

## Team

| Name | Student ID |
|---|---|
| V.A. Riviru Eren - Project Lead | s8170544 |
| P.H. Movindi Amasha | s8170573 |
| M.N.R. Marasingha | s8170623 |
| R.M.T.D. Moragolla | s8170624 |

**Victoria University**
<img width="120" height="62" alt="Victoria University" src="https://github.com/user-attachments/assets/b9c555f6-ea69-4655-ba9e-118d6e05ebc4" />
