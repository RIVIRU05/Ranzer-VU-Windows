"""
RANZER - File System Watcher (Windows)
Real-time filesystem event listener using watchdog.

Key design decisions:
- on_created only counts toward write rate (actual new files)
- on_modified only does entropy check (can fire on reads too)
- Interactive/system processes are whitelisted and never flagged
- PID detection uses psutil.open_files() (Windows equivalent of /proc/fd scan)
- Write rate tracking uses psutil.io_counters().write_bytes (Windows equivalent of wchar)
"""

import logging
import os
import threading
import time
from collections import defaultdict
from pathlib import Path
from typing import Optional, Callable

try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    FileSystemEventHandler = object

from .entropy_monitor import EntropyMonitor
from .honey_file_engine import HoneyFileEngine

logger = logging.getLogger("ranzer.watcher")


def _norm(name: str) -> str:
    """Lowercase and strip .exe suffix."""
    return name.lower().removesuffix(".exe")


# Processes that are always user-interactive — never flag these
INTERACTIVE_PROCESS_WHITELIST = {
    # Shell / file manager
    "explorer", "cmd", "powershell", "pwsh", "wt", "conhost", "windowsterminal",
    # Text editors
    "notepad", "wordpad", "notepad++", "code", "devenv", "sublime_text",
    # Office
    "winword", "excel", "powerpnt", "outlook", "onenote",
    # Browsers
    "chrome", "firefox", "msedge", "iexplore", "brave", "opera",
    # Document / media viewers
    "acrord32", "acrobat", "foxitreader", "vlc", "wmplayer", "photos", "mspaint",
    # System processes — killing these would brick Windows
    "system", "smss", "csrss", "wininit", "winlogon",
    "services", "lsass", "lsm", "svchost", "dwm",
    "taskhostw", "taskmgr", "spoolsv", "searchindexer",
    "wuauclt", "msiexec", "dllhost", "rundll32",
    "ctfmon", "sihost", "runtimebroker", "applicationframehost",
    "shellexperiencehost", "startmenuexperiencehost", "searchapp",
    "fontdrvhost", "audiodg",
    # Security
    "msmpeng", "mssense", "securityhealthservice",
    # Cloud sync — legitimately writes a lot
    "onedrive", "dropbox", "googledrivesync", "googledrive",
    # RANZER itself
    "ranzer",
    # NOTE: python/python3/git intentionally NOT whitelisted — same as process_tracker.
}

_INTERACTIVE_PREFIXES = {
    "svchost", "wmi", "ntoskrnl", "microsoft.", "msft.", "windows.", "onedrive",
}


def _is_interactive_process(name: str) -> bool:
    n = _norm(name)
    return n in INTERACTIVE_PROCESS_WHITELIST or any(n.startswith(p) for p in _INTERACTIVE_PREFIXES)


def _get_pid_of_file(file_path: str) -> list:
    """
    Use psutil to find which PIDs have file_path open right now.
    Windows equivalent of scanning /proc/*/fd.
    Returns list of (pid, process_name).
    """
    results = []
    try:
        import psutil
        target = str(Path(file_path).resolve()).lower()
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                for f in proc.open_files():
                    if f.path.lower() == target:
                        results.append((proc.info["pid"], proc.info["name"] or ""))
                        break
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return results


def _get_high_write_pids(monitored_dir: str) -> list:
    """
    Fallback: use psutil to find processes with multiple files open in monitored_dir.
    Returns list of (pid, name, open_count).
    """
    results = []
    try:
        import psutil
        for proc in psutil.process_iter(["pid", "name"]):
            try:
                name = proc.info["name"] or ""
                if _is_interactive_process(name):
                    continue
                matching = [
                    f.path for f in proc.open_files()
                    if f.path.lower().startswith(monitored_dir.lower())
                ]
                if len(matching) >= 3:
                    results.append((proc.pid, name, len(matching)))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
    except Exception:
        pass
    return results


class _Handler(FileSystemEventHandler if WATCHDOG_AVAILABLE else object):
    def __init__(self, entropy_monitor, honey_file_engine,
                 max_file_size=10*1024*1024,
                 pid_alert_callback=None,
                 monitored_dirs=None,
                 quarantined_pids=None):
        if WATCHDOG_AVAILABLE:
            super().__init__()
        self.entropy_monitor = entropy_monitor
        self.honey_file_engine = honey_file_engine
        self.max_file_size = max_file_size
        self.pid_alert_callback = pid_alert_callback
        self.monitored_dirs = monitored_dirs or []
        self.events_processed = 0
        # Shared reference to ProcessBehaviorTracker._quarantined_pids so we
        # can suppress events from already-terminated processes immediately.
        self._quarantined_pids: set = quarantined_pids if quarantined_pids is not None else set()

        self._write_counts: dict = defaultdict(list)
        self._alerted_pids: set = set()
        self._lock = threading.Lock()
        self._wchar_prev: dict = {}   # pid -> (timestamp, write_bytes)
        self._wchar_rate: dict = {}   # pid -> (bytes_per_sec, name)
        self._last_wchar_snap: float = 0.0

    # ------------------------------------------------------------------ #
    # Watchdog event handlers                                              #
    # ------------------------------------------------------------------ #

    def on_modified(self, event):
        if not event.is_directory:
            self._entropy_only(event.src_path)

    def on_created(self, event):
        if not event.is_directory:
            self._full_check(event.src_path)

    def on_deleted(self, event):
        if not event.is_directory and self.honey_file_engine.is_honey_file(event.src_path):
            self.honey_file_engine.check_file(event.src_path, event_type="deleted")

    def on_moved(self, event):
        if not event.is_directory and self.honey_file_engine.is_honey_file(event.src_path):
            self.honey_file_engine.check_file(event.src_path, event_type="renamed")

    # ------------------------------------------------------------------ #
    # Internal routing                                                     #
    # ------------------------------------------------------------------ #

    def _entropy_only(self, file_path: str):
        if self.honey_file_engine.is_honey_file(file_path):
            self.honey_file_engine.check_file(file_path, event_type="modified")
            return

        try:
            size = Path(file_path).stat().st_size
            if size == 0 or size > self.max_file_size:
                return
        except OSError:
            return

        pid, name = self._detect_pid(file_path)
        self.entropy_monitor.analyze_file(file_path, process_pid=pid, process_name=name)

    def _full_check(self, file_path: str):
        self.events_processed += 1

        if self.honey_file_engine.is_honey_file(file_path):
            self.honey_file_engine.check_file(file_path, event_type="modified")

        parent = str(Path(file_path).parent)
        now = time.time()
        with self._lock:
            self._write_counts[parent].append(now)
            self._write_counts[parent] = [
                t for t in self._write_counts[parent] if now - t <= 5.0
            ]
            rate = len(self._write_counts[parent])

        if rate >= 10 and self.pid_alert_callback:
            self._snapshot_wchar()
            self._find_and_report_pid(file_path, rate)

        try:
            size = Path(file_path).stat().st_size
            if size == 0 or size > self.max_file_size:
                return
        except OSError:
            return

        pid, name = self._detect_pid(file_path)
        self.entropy_monitor.analyze_file(file_path, process_pid=pid, process_name=name)

    def _snapshot_wchar(self):
        """
        Sample write_bytes for all non-interactive processes via psutil.
        Windows equivalent of reading /proc/*/io wchar.
        Throttled to 2x/s.
        """
        now = time.time()
        if now - self._last_wchar_snap < 0.5:
            return
        self._last_wchar_snap = now
        try:
            import psutil
            for proc in psutil.process_iter(["pid", "name"]):
                try:
                    pid = proc.info["pid"]
                    name = proc.info["name"] or ""
                    if pid <= 4 or pid == os.getpid():
                        continue
                    if _is_interactive_process(name):
                        continue
                    io = proc.io_counters()
                    write_bytes = io.write_bytes
                    if pid in self._wchar_prev:
                        prev_t, prev_w = self._wchar_prev[pid]
                        elapsed = now - prev_t
                        if elapsed > 0:
                            self._wchar_rate[pid] = ((write_bytes - prev_w) / elapsed, name)
                    self._wchar_prev[pid] = (now, write_bytes)
                except (psutil.NoSuchProcess, psutil.AccessDenied,
                        psutil.ZombieProcess, NotImplementedError):
                    continue
        except Exception:
            pass

    def _detect_pid(self, file_path: str):
        """
        Best-effort: identify the writing PID from the wchar rate snapshot.
        Using the snapshot is O(1) and avoids iterating all processes per file
        event (which is very slow on Windows via psutil.open_files).
        """
        if not self._wchar_rate:
            return None, None
        candidates = [
            (pid, name)
            for pid, (rate, name) in self._wchar_rate.items()
            if rate > 10 * 1024  # >10 KB/s — actively writing
            and pid != os.getpid() and pid > 4
            and pid not in self._quarantined_pids
            and not _is_interactive_process(name)
        ]
        if not candidates:
            return None, None
        # Return the highest write-rate candidate
        candidates.sort(key=lambda x: self._wchar_rate[x[0]][0], reverse=True)
        return candidates[0]

    def _find_and_report_pid(self, file_path: str, rate: int):
        """Find which PID created this file and fire the callback if suspicious."""
        # Method 1: psutil open_files scan
        pids = _get_pid_of_file(file_path)
        pids = [(pid, name) for pid, name in pids
                if not _is_interactive_process(name) and pid != os.getpid() and pid > 4]

        # Method 2: psutil fallback — find processes with many files open in parent dir
        if not pids:
            parent = str(Path(file_path).parent)
            pids = [(p, n) for p, n, _ in _get_high_write_pids(parent)
                    if p != os.getpid() and p > 4]

        # Method 3: write_bytes rate — catches scripts that close files quickly
        if not pids and self._wchar_rate:
            HIGH = 50 * 1024  # 50 KB/s sustained
            candidates = [
                (pid, name)
                for pid, (r, name) in self._wchar_rate.items()
                if r > HIGH and pid != os.getpid() and pid > 4
                and not _is_interactive_process(name)
            ]
            if candidates:
                candidates.sort(key=lambda x: self._wchar_rate[x[0]][0], reverse=True)
                pids = [candidates[0]]

        for pid, name in pids:
            if pid in self._alerted_pids:
                continue
            if pid in self._quarantined_pids:
                continue
            self._alerted_pids.add(pid)
            logger.warning(
                f"[WATCHER] Suspicious writer: PID {pid} ({name}) | "
                f"{rate} new files in 5s"
            )
            if self.pid_alert_callback:
                self.pid_alert_callback(pid, name, rate, file_path)


class FileSystemWatcher:
    def __init__(self, entropy_monitor, honey_file_engine,
                 recursive=True, pid_alert_callback=None, quarantined_pids=None):
        if not WATCHDOG_AVAILABLE:
            raise RuntimeError("watchdog not installed. Run: pip install watchdog")
        self.recursive = recursive
        self._observer = None
        self._dirs: set = set()
        self._running = False
        self._lock = threading.Lock()
        self._handler = _Handler(
            entropy_monitor, honey_file_engine,
            pid_alert_callback=pid_alert_callback,
            quarantined_pids=quarantined_pids,
        )

    def add_directory(self, directory: str):
        directory = str(Path(directory).resolve())
        if not Path(directory).is_dir():
            logger.warning(f"Not a directory: {directory}")
            return
        with self._lock:
            if directory in self._dirs:
                return
            self._dirs.add(directory)
            self._handler.monitored_dirs.append(directory)
            if self._running and self._observer:
                self._observer.schedule(self._handler, directory, recursive=self.recursive)
                logger.info(f"[WATCHER] Added: {directory}")

    def start(self):
        if not self._dirs or self._running:
            return
        self._observer = Observer()
        with self._lock:
            for d in self._dirs:
                self._observer.schedule(self._handler, d, recursive=self.recursive)
                logger.info(f"[WATCHER] Watching: {d}")
        self._observer.start()
        self._running = True
        logger.info("[WATCHER] Started.")

    def stop(self):
        if not self._running or not self._observer:
            return
        self._observer.stop()
        self._observer.join(timeout=5)
        self._running = False
        logger.info("[WATCHER] Stopped.")

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def monitored_directories(self) -> list:
        return list(self._dirs)

    @property
    def events_processed(self) -> int:
        return self._handler.events_processed
