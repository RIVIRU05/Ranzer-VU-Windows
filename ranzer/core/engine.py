"""
RANZER - Main Engine Orchestrator
Single entry point that starts/stops all detection subsystems.
Used by both CLI and GUI.
"""

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

from .entropy_monitor import EntropyMonitor, EntropyEvent
from .honey_file_engine import HoneyFileEngine, HoneyFileEvent
from .process_tracker import ProcessBehaviorTracker, ProcessEvent
from .threat_correlator import ThreatCorrelator, ThreatAssessment
from .alert_handler import AlertHandler, setup_logging
from .file_watcher import FileSystemWatcher

logger = logging.getLogger("ranzer.engine")


@dataclass
class RanzerConfig:
    monitored_dirs: list = field(default_factory=list)
    entropy_threshold: float = 7.5
    max_file_size_mb: int = 10
    honey_files_per_dir: int = 2
    process_scan_interval: float = 0.5  # scan every 0.5s for faster PID detection
    honey_scan_interval: float = 10.0
    file_access_threshold: int = 20
    rate_threshold: float = 10.0
    enable_desktop_alerts: bool = True
    enable_process_tracking: bool = True
    enable_honey_files: bool = True
    enable_entropy_monitoring: bool = True
    enable_auto_terminate: bool = False
    recursive_watch: bool = True
    log_dir: str = "."
    honey_state_file: str = ".ranzer_honey_state.json"
    testing_mode: bool = False  # if True, python3 is not whitelisted (for simulator testing)


class RanzerEngine:
    def __init__(self, config: Optional[RanzerConfig] = None):
        self.config = config or RanzerConfig()
        self._running = False
        self._threads: list = []
        self._stop_event = threading.Event()

        # If log_dir is the default "." resolve it relative to user home so the
        # installed .exe (which starts in C:\Program Files\Ranzer\) doesn't try
        # to write logs there without permission.
        if self.config.log_dir == ".":
            self.config.log_dir = str(Path.home() / "RANZER_logs")
        log_dir = str(Path(self.config.log_dir).resolve())
        self.config.log_dir = log_dir

        log_path = setup_logging(level=logging.INFO, log_dir=log_dir)
        logger.info(f"RANZER initialised — log: {log_path}")
        try:
            import ctypes
            if ctypes.windll.shell32.IsUserAnAdmin():
                logger.warning("Running as Administrator — system processes are whitelisted")
        except Exception:
            pass

        self.alert_handler = AlertHandler(
            log_file=str(Path(log_dir) / "ranzer_events.log"),
            enable_desktop_alerts=self.config.enable_desktop_alerts,
        )
        self.entropy_monitor = EntropyMonitor(
            threshold=self.config.entropy_threshold,
            max_file_size=self.config.max_file_size_mb * 1024 * 1024,
            alert_callback=self._on_entropy,
        )
        self.honey_file_engine = HoneyFileEngine(alert_callback=self._on_honey)
        # Always protect kernel, RANZER itself, and the shell/process that launched it
        _safe_pids = {0, 1, 2, os.getpid(), os.getppid()}
        self.process_tracker = ProcessBehaviorTracker(
            file_access_threshold=self.config.file_access_threshold,
            rate_threshold=self.config.rate_threshold,
            alert_callback=self._on_process,
            monitored_dirs=list(self.config.monitored_dirs),
            testing_mode=self.config.testing_mode,
            ignored_pids=_safe_pids,
        )
        self.correlator = ThreatCorrelator(auto_action_callback=self._on_assessment)
        self.file_watcher = FileSystemWatcher(
            entropy_monitor=self.entropy_monitor,
            honey_file_engine=self.honey_file_engine,
            recursive=self.config.recursive_watch,
            pid_alert_callback=self._on_rapid_write_pid,
            quarantined_pids=self.process_tracker._quarantined_pids,
        )

    def start(self):
        if self._running:
            return
        self._stop_event.clear()
        self._running = True

        for d in self.config.monitored_dirs:
            self.file_watcher.add_directory(d)

        if self.config.enable_honey_files and self.config.monitored_dirs:
            deployed = self.honey_file_engine.deploy_to_directories(
                self.config.monitored_dirs, count_per_dir=self.config.honey_files_per_dir
            )
            for path in deployed:
                self.process_tracker.add_honey_file(path)
            self.honey_file_engine.save_state(self.config.honey_state_file)

        if self.config.enable_entropy_monitoring or self.config.enable_honey_files:
            self.file_watcher.start()

        if self.config.enable_process_tracking:
            t = threading.Thread(target=self._process_loop, daemon=True, name="ranzer-process")
            t.start()
            self._threads.append(t)

        if self.config.enable_honey_files:
            t = threading.Thread(target=self._honey_loop, daemon=True, name="ranzer-honey")
            t.start()
            self._threads.append(t)

        logger.info(f"RANZER active — watching {len(self.config.monitored_dirs)} directories.")

    def stop(self):
        if not self._running:
            return
        self._stop_event.set()
        self._running = False
        self.file_watcher.stop()
        for t in self._threads:
            t.join(timeout=5)
        self._threads.clear()
        if self.config.enable_honey_files:
            self.honey_file_engine.remove_all()
        logger.info("RANZER stopped.")

    @property
    def is_running(self) -> bool:
        return self._running

    def add_directory(self, directory: str):
        self.config.monitored_dirs.append(directory)
        self.file_watcher.add_directory(directory)
        self.process_tracker.add_monitored_dir(directory)
        if self.config.enable_honey_files:
            deployed = self.honey_file_engine.deploy(directory, count=self.config.honey_files_per_dir)
            for path in deployed:
                self.process_tracker.add_honey_file(path)

    def set_entropy_threshold(self, threshold: float):
        self.entropy_monitor.set_threshold(threshold)
        self.config.entropy_threshold = threshold

    def get_status(self) -> dict:
        return {
            "running": self._running,
            "monitored_dirs": self.config.monitored_dirs,
            "events_processed": self.file_watcher.events_processed,
            "honey_files_deployed": len(self.honey_file_engine.get_registered_paths()),
            "alert_counts": self.alert_handler.get_alert_counts(),
            "entropy_threshold": self.config.entropy_threshold,
            "auto_terminate": self.config.enable_auto_terminate,
        }

    def get_recent_alerts(self, limit: int = 50) -> list:
        return self.alert_handler.get_alerts(limit=limit)

    def export_alerts(self, path: str, fmt: str = "json"):
        if fmt == "json":
            self.alert_handler.export_json(path)
        elif fmt == "csv":
            self.alert_handler.export_csv(path)
        elif fmt == "txt":
            self.alert_handler.export_txt(path)

    # Callbacks
    def _on_entropy(self, event: EntropyEvent):
        self.alert_handler.handle_event(event)
        self.alert_handler.handle_assessment(self.correlator.ingest(event))

    def _on_honey(self, event: HoneyFileEvent):
        self.alert_handler.handle_event(event)
        self.alert_handler.handle_assessment(self.correlator.ingest(event))

    def _on_process(self, event: ProcessEvent):
        self.alert_handler.handle_event(event)
        self.alert_handler.handle_assessment(self.correlator.ingest(event))

    def _on_assessment(self, assessment: ThreatAssessment):
        logger.critical(f"[THREAT] {assessment.threat_level} score={assessment.threat_score:.1f} "
                        f"action={assessment.recommended_action} PIDs={assessment.correlated_pids}")
        if self.config.enable_auto_terminate and assessment.recommended_action == "TERMINATE":
            if assessment.correlated_pids:
                for pid in assessment.correlated_pids:
                    if pid in self.process_tracker._quarantined_pids:
                        continue
                    if not self.process_tracker.terminate_process(pid):
                        self.process_tracker.kill_process(pid)
            elif self.config.monitored_dirs:
                # Entropy pushed threat to CRITICAL but write rate was too low to
                # identify the PID through normal scanning — do an emergency lookup
                found = self.process_tracker.find_writers_targeting_dirs(
                    self.config.monitored_dirs
                )
                for event in found:
                    # Route through the tracker's callback so the GUI Actions
                    # pane and alert handler both receive this event.
                    cb = self.process_tracker.alert_callback
                    if cb:
                        cb(event)
                    else:
                        self.alert_handler.handle_event(event)
                    # cb() may have already terminated this PID via re-entrant
                    # _on_assessment — skip if already quarantined to avoid the
                    # "process not found" error log.
                    if event.pid not in self.process_tracker._quarantined_pids:
                        if not self.process_tracker.terminate_process(event.pid):
                            self.process_tracker.kill_process(event.pid)

    def _on_rapid_write_pid(self, pid: int, name: str, rate: int, file_path: str):
        """Called by file watcher when a PID is caught writing files rapidly."""
        from .process_tracker import ProcessEvent
        logger.warning(
            f"[ENGINE] Rapid write PID caught: {name} (PID {pid}) | "
            f"rate={rate} files/5s | file={file_path}"
        )
        event = ProcessEvent(
            pid=pid, process_name=name, exe_path=None,
            event_reason="rapid_file_writes_detected",
            open_file_count=rate, file_access_rate=rate / 5.0,
            flagged_files=[file_path],
        )
        # Route through process_tracker so the event appears in System Actions
        # and fires the GUI event queue. _on_process handles alert_handler +
        # correlator, so we only need to check auto-terminate here.
        self.process_tracker.record_external_event(event)

        # Only auto-terminate if threat score is HIGH or CRITICAL
        # (entropy must have also fired — rapid writes alone are not enough)
        if self.config.enable_auto_terminate:
            latest = self.correlator.get_latest_assessment()
            if latest and latest.threat_level in ("HIGH", "CRITICAL"):
                logger.warning(
                    f"[ENGINE] Auto-terminating PID {pid} ({name}) — "
                    f"threat={latest.threat_level} score={latest.threat_score:.1f}"
                )
                if not self.process_tracker.terminate_process(pid):
                    self.process_tracker.kill_process(pid)
            else:
                logger.info(
                    f"[ENGINE] Rapid writes from PID {pid} ({name}) — "
                    f"NOT terminating, entropy threshold not yet reached"
                )

    def _process_loop(self):
        while not self._stop_event.is_set():
            try:
                self.process_tracker.scan()
            except Exception as e:
                logger.error(f"Process scan error: {e}")
            self._stop_event.wait(timeout=self.config.process_scan_interval)

    def _honey_loop(self):
        while not self._stop_event.is_set():
            try:
                self.honey_file_engine.scan_all()
            except Exception as e:
                logger.error(f"Honey scan error: {e}")
            self._stop_event.wait(timeout=self.config.honey_scan_interval)
