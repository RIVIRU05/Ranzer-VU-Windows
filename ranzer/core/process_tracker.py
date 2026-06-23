"""
RANZER - Process Behavior Tracker (Windows)
Monitors running processes for ransomware-like behavior using psutil.

Detection logic:
- Watches processes writing to monitored directories at high rates
- Uses psutil.io_counters() to track write volume (Windows equivalent of /proc/io wchar)
- Whitelists known user-interactive and system processes
- Requires BOTH high write rate AND high entropy signals before terminating
"""

import os
import time
import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger("ranzer.process")


def _norm(name: str) -> str:
    """Normalize process name: lowercase and strip .exe suffix."""
    return name.lower().removesuffix(".exe")


# ------------------------------------------------------------------ #
# Whitelist — these processes are NEVER flagged in normal scanning    #
# ------------------------------------------------------------------ #
WHITELISTED_PROCESSES = {
    # Windows shell and file managers
    "explorer",
    # Text editors
    "notepad", "wordpad", "notepad++", "mousepad",
    "code", "devenv", "sublime_text", "atom",
    # Microsoft Office
    "winword", "excel", "powerpnt", "outlook", "onenote", "msaccess",
    # Browsers
    "chrome", "firefox", "msedge", "iexplore", "brave", "opera",
    # Terminals / shells
    "cmd", "powershell", "pwsh", "wt", "conhost",
    "windowsterminal",
    # Document viewers / media
    "acrord32", "acrobat", "foxitreader", "vlc", "wmplayer",
    "photos", "mspaint", "paint",
    # System processes — NEVER terminate these
    "system", "smss", "csrss", "wininit", "winlogon",
    "services", "lsass", "lsm", "svchost", "dwm",
    "taskhost", "taskhostw", "taskmgr",
    "spoolsv", "searchindexer", "searchprotocolhost",
    "wuauclt", "trustedinstaller", "tiworker",
    "msiexec", "dllhost", "rundll32", "regsvr32",
    "ctfmon", "sihost", "runtimebroker",
    "applicationframehost", "shellexperiencehost",
    "startmenuexperiencehost", "searchapp",
    "fontdrvhost", "audiodg",
    # Windows Defender / Security Center
    "msmpeng", "mssense", "securityhealthservice",
    "securityhealthsystray",
    # Windows Update services
    "wuauclt", "usoclient", "musnotification",
    # OneDrive / cloud sync — high write volume but not ransomware
    "onedrive", "dropbox", "googledrivesync", "googledrive",
    # RANZER itself
    "ranzer",
    # NOTE: python/python3/git intentionally NOT whitelisted.
    # Real ransomware uses these (LotL). The 100KB/s threshold
    # prevents false positives from normal dev usage.
}

# Prefixes for system service names — checked after stripping .exe
WHITELISTED_PREFIXES = {
    "svchost",
    "wmi",
    "ntoskrnl",
    "microsoft.",
    "msft.",
    "windows.",
    "onedrive",
}

# Live-off-the-land tools — whitelisted in normal scan but catchable
# when entropy is already CRITICAL
LOTL_TOOLS = {
    "openssl", "gpg", "gpg2",
    "python", "python3",
    "7z", "winrar", "wzzip",
    "robocopy", "xcopy",
    "certutil",   # often abused for base64 encoding
    "wscript", "cscript",
    "powershell", "pwsh",
}


@dataclass
class ProcessEvent:
    pid: int
    process_name: str
    exe_path: Optional[str]
    event_reason: str
    open_file_count: int
    file_access_rate: float
    write_bytes_per_sec: float = 0.0
    flagged_files: list = field(default_factory=list)
    timestamp: float = field(default_factory=time.time)

    @property
    def severity(self) -> str:
        if "honeyfile" in self.event_reason:
            return "CRITICAL"
        elif self.event_reason == "entropy_correlated_writer":
            return "HIGH"
        elif self.write_bytes_per_sec > 500 * 1024:
            return "HIGH"
        elif self.file_access_rate > 20:
            return "MEDIUM"
        return "LOW"

    def to_dict(self) -> dict:
        return {
            "type": "process",
            "pid": self.pid,
            "process_name": self.process_name,
            "exe_path": self.exe_path,
            "event_reason": self.event_reason,
            "open_file_count": self.open_file_count,
            "file_access_rate": round(self.file_access_rate, 2),
            "write_bytes_per_sec": round(self.write_bytes_per_sec, 0),
            "severity": self.severity,
            "flagged_files": self.flagged_files[:10],
            "timestamp": self.timestamp,
        }


def _read_proc_io(pid: int) -> Optional[dict]:
    """
    Get I/O counters for a process via psutil.
    Returns dict with 'wchar' key (write_bytes on Windows) or None.
    """
    try:
        proc = psutil.Process(pid)
        io = proc.io_counters()
        return {"wchar": io.write_bytes}
    except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess,
            NotImplementedError, AttributeError):
        return None


def _get_proc_open_files_in_dir(pid: int, monitored_dirs: list) -> list:
    """Get list of files this PID has open that are in any monitored directory."""
    result = []
    try:
        proc = psutil.Process(pid)
        for f in proc.open_files():
            fpath = f.path.lower()
            for d in monitored_dirs:
                if fpath.startswith(d.lower()):
                    result.append(f.path)
                    break
    except (psutil.NoSuchProcess, psutil.AccessDenied, OSError):
        pass
    return result


def _proc_targets_monitored_dir(pid: int, monitored_dirs: list) -> bool:
    """
    Check process cwd and cmdline to confirm it is targeting a monitored directory.
    Used when open_files() misses quickly-closed files.
    """
    try:
        proc = psutil.Process(pid)
        try:
            cwd = proc.cwd().lower()
            for d in monitored_dirs:
                if cwd.startswith(d.lower()):
                    return True
        except (psutil.AccessDenied, OSError):
            pass
        try:
            cmdline = " ".join(proc.cmdline()).lower()
            for d in monitored_dirs:
                if d.lower() in cmdline:
                    return True
        except (psutil.AccessDenied, OSError):
            pass
    except (psutil.NoSuchProcess, psutil.AccessDenied):
        pass
    return False


class _ProcIOSnapshot:
    """Tracks process write_bytes over time to calculate write rate."""

    def __init__(self, pid: int):
        self.pid = pid
        self._samples: list = []  # (timestamp, write_bytes)

    def sample(self) -> bool:
        """Take a sample. Returns False if process is gone."""
        io = _read_proc_io(self.pid)
        if io is None:
            return False
        write_bytes = io.get("wchar", 0)
        self._samples.append((time.time(), write_bytes))
        cutoff = time.time() - 10.0
        self._samples = [(t, b) for t, b in self._samples if t > cutoff]
        return True

    def write_rate_bytes_per_sec(self, window: float = 5.0) -> float:
        cutoff = time.time() - window
        recent = [(t, b) for t, b in self._samples if t > cutoff]
        if len(recent) < 2:
            return 0.0
        elapsed = recent[-1][0] - recent[0][0]
        if elapsed <= 0:
            return 0.0
        delta_bytes = recent[-1][1] - recent[0][1]
        return max(0.0, delta_bytes / elapsed)

    def write_syscalls_per_sec(self, window: float = 5.0) -> float:
        return self.write_rate_bytes_per_sec(window)


class ProcessBehaviorTracker:
    """
    Tracks process I/O behavior via psutil for accurate write detection on Windows.

    Flags processes that:
    1. Write data at high rates (>100KB/s sustained)
    2. Have many files open simultaneously in monitored directories
    3. Access honey files
    """

    WRITE_RATE_THRESHOLD_BYTES = 100 * 1024  # 100KB/s

    OPEN_FILES_THRESHOLD = 10

    def __init__(
        self,
        file_access_threshold: int = 10,
        rate_threshold: float = 10.0,
        honey_file_paths: Optional[list] = None,
        alert_callback=None,
        ignored_pids: Optional[set] = None,
        monitored_dirs: Optional[list] = None,
        testing_mode: bool = False,
    ):
        if not PSUTIL_AVAILABLE:
            logger.error("psutil not installed. Run: pip install psutil")

        self.file_access_threshold = file_access_threshold
        self.rate_threshold = rate_threshold
        self.honey_file_paths: set = set(honey_file_paths or [])
        self.alert_callback = alert_callback
        self.ignored_pids: set = ignored_pids or {0, 4}  # 0=Idle, 4=System on Windows
        self.monitored_dirs: list = monitored_dirs or []
        self.testing_mode = testing_mode

        self._io_snapshots: dict = {}
        self._alerted_pids: set = set()
        self._event_history: list = []
        self._quarantined_pids: set = set()

    def scan(self) -> list:
        if not PSUTIL_AVAILABLE:
            return []

        events = []
        whitelist = set(WHITELISTED_PROCESSES)

        for proc in psutil.process_iter(["pid", "name", "exe"]):
            try:
                pid = proc.info["pid"]
                name = _norm(proc.info["name"] or "")

                if pid in self.ignored_pids:
                    continue
                if pid in self._quarantined_pids:
                    continue
                if pid == os.getpid():
                    continue
                if name in whitelist:
                    continue
                if any(name.startswith(p) for p in WHITELISTED_PREFIXES):
                    continue
                if pid in self._alerted_pids:
                    continue

                if pid not in self._io_snapshots:
                    self._io_snapshots[pid] = _ProcIOSnapshot(pid)
                alive = self._io_snapshots[pid].sample()
                if not alive:
                    continue

                write_rate = self._io_snapshots[pid].write_rate_bytes_per_sec()

                open_in_monitored = []
                if self.monitored_dirs:
                    open_in_monitored = _get_proc_open_files_in_dir(pid, self.monitored_dirs)

                honey_hits = [p for p in open_in_monitored if p in self.honey_file_paths]

                event = None

                if honey_hits:
                    event = self._build(
                        proc, len(open_in_monitored), write_rate,
                        "honeyfile_access", honey_hits, write_rate,
                    )
                elif write_rate > self.WRITE_RATE_THRESHOLD_BYTES:
                    touches = (
                        open_in_monitored
                        or not self.monitored_dirs
                        or _proc_targets_monitored_dir(pid, self.monitored_dirs)
                    )
                    if touches:
                        event = self._build(
                            proc, len(open_in_monitored), write_rate / 1024,
                            "high_write_rate", open_in_monitored[:10], write_rate,
                        )
                elif len(open_in_monitored) > self.OPEN_FILES_THRESHOLD:
                    event = self._build(
                        proc, len(open_in_monitored), write_rate / 1024,
                        "high_open_file_count", open_in_monitored[:10], write_rate,
                    )

                if event:
                    self._alerted_pids.add(pid)
                    self._event_history.append(event)
                    events.append(event)
                    logger.warning(
                        f"[PROCESS] {event.severity} | PID {pid} ({name}) | "
                        f"reason={event.event_reason} | "
                        f"write_rate={write_rate/1024:.1f}KB/s | "
                        f"open_files={len(open_in_monitored)}"
                    )
                    if self.alert_callback:
                        self.alert_callback(event)

            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue

        try:
            active = {p.pid for p in psutil.process_iter(["pid"])}
            for pid in list(self._io_snapshots.keys()):
                if pid not in active:
                    del self._io_snapshots[pid]
                    self._alerted_pids.discard(pid)
        except Exception:
            pass

        return events

    def terminate_process(self, pid: int) -> bool:
        if not PSUTIL_AVAILABLE:
            return False
        try:
            proc = psutil.Process(pid)
            name = proc.name()
            proc.terminate()
            proc.wait(timeout=3)
            self._quarantined_pids.add(pid)
            logger.warning(f"[PROCESS] Terminated PID {pid} ({name})")
            return True
        except Exception as e:
            logger.error(f"Could not terminate PID {pid}: {e}")
            return False

    def kill_process(self, pid: int) -> bool:
        if not PSUTIL_AVAILABLE:
            return False
        try:
            proc = psutil.Process(pid)
            proc.kill()
            self._quarantined_pids.add(pid)
            logger.warning(f"[PROCESS] Killed PID {pid}")
            return True
        except Exception as e:
            logger.error(f"Could not kill PID {pid}: {e}")
            return False

    def get_process_info(self, pid: int) -> Optional[dict]:
        if not PSUTIL_AVAILABLE:
            return None
        try:
            proc = psutil.Process(pid)
            return {
                "pid": pid,
                "name": proc.name(),
                "exe": proc.exe(),
                "status": proc.status(),
                "cpu_percent": proc.cpu_percent(interval=0.1),
                "memory_mb": round(proc.memory_info().rss / (1024 * 1024), 1),
                "open_files": len(proc.open_files()),
            }
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return None

    def find_writers_targeting_dirs(self, dirs: list) -> list:
        """
        Emergency scan at CRITICAL entropy: find processes whose cwd or cmdline
        references a monitored directory. LotL tools are NOT excluded here.
        """
        if not PSUTIL_AVAILABLE:
            return []

        events = []
        whitelist = set(WHITELISTED_PROCESSES) - LOTL_TOOLS

        for proc in psutil.process_iter(["pid", "name"]):
            try:
                pid = proc.info["pid"]
                name = _norm(proc.info["name"] or "")
                if pid in self.ignored_pids or pid == os.getpid():
                    continue
                if name in whitelist:
                    continue
                if any(name.startswith(p) for p in WHITELISTED_PREFIXES):
                    continue
                if pid in self._quarantined_pids or pid in self._alerted_pids:
                    continue
                if _proc_targets_monitored_dir(pid, dirs):
                    event = self._build(proc, 0, 0.0, "entropy_correlated_writer", [], 0.0)
                    self._alerted_pids.add(pid)
                    self._event_history.append(event)
                    events.append(event)
                    logger.warning(
                        f"[PROCESS] Emergency scan found PID {pid} ({name}) "
                        f"targeting monitored dir"
                    )
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
        return events

    def add_honey_file(self, path: str):
        self.honey_file_paths.add(path)

    def add_monitored_dir(self, directory: str):
        if directory not in self.monitored_dirs:
            self.monitored_dirs.append(directory)

    def is_quarantined(self, pid: int) -> bool:
        return pid in self._quarantined_pids

    def record_external_event(self, event: "ProcessEvent"):
        self._event_history.append(event)
        self._alerted_pids.add(event.pid)
        if self.alert_callback:
            self.alert_callback(event)

    def synthesize_event_for_pid(self, pid: int, reason: str,
                                  alert_handler=None, alert_callback=None):
        """
        Build a ProcessEvent for a PID detected via correlator (not process scan).
        Routes to the GUI Actions pane and alert log — without this the
        correlated_pids termination path leaves the Actions pane empty.
        """
        if pid in self._alerted_pids:
            return
        try:
            proc = psutil.Process(pid)
            event = self._build(proc, 0, 0.0, reason, [], 0.0)
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return
        self._alerted_pids.add(pid)
        self._event_history.append(event)
        logger.warning(
            f"[PROCESS] Correlated PID {pid} ({event.process_name}) flagged "
            f"via entropy correlation — reason={reason}"
        )
        if alert_callback:
            alert_callback(event)
        elif alert_handler:
            alert_handler.handle_event(event)

    def get_recent_events(self, limit: int = 50) -> list:
        return self._event_history[-limit:]

    def clear_history(self):
        self._event_history.clear()
        self._alerted_pids.clear()

    def _build(self, proc, open_count, rate, reason,
               flagged, write_bytes_per_sec=0.0) -> ProcessEvent:
        try:
            exe = proc.exe()
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            exe = None
        return ProcessEvent(
            pid=proc.pid,
            process_name=proc.name(),
            exe_path=exe,
            event_reason=reason,
            open_file_count=open_count,
            file_access_rate=rate,
            write_bytes_per_sec=write_bytes_per_sec,
            flagged_files=flagged,
        )
