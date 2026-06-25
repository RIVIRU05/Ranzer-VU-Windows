"""
RANZER - Alert Handler
Routes all detection events to: file log, desktop notification, in-memory queue, export.
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Union

from .entropy_monitor import EntropyEvent
from .honey_file_engine import HoneyFileEvent
from .process_tracker import ProcessEvent
from .threat_correlator import ThreatAssessment

AnyEvent = Union[EntropyEvent, HoneyFileEvent, ProcessEvent]
logger = logging.getLogger("ranzer.alerts")
_SEV = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}


def _fmt(ts: float) -> str:
    return datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")


class AlertHandler:
    def __init__(self, log_file: str = "ranzer_events.log",
                 enable_desktop_alerts: bool = True,
                 min_severity_for_desktop: str = "MEDIUM",
                 max_queue_size: int = 500,
                 escalation_callback=None):
        self.enable_desktop_alerts = enable_desktop_alerts
        self.min_severity_for_desktop = min_severity_for_desktop
        self.max_queue_size = max_queue_size
        self.escalation_callback = escalation_callback
        self._max_notified_level = -1   # tracks highest level already notified
        self._queue: list = []

        # Always save logs into a logs/ subfolder with a dated filename
        # e.g. logs/ranzer_events_2026-04-25.log
        # This means logs persist forever, one file per day, never overwritten
        base_dir = Path(log_file).parent
        logs_dir = base_dir / "logs"
        logs_dir.mkdir(parents=True, exist_ok=True)

        today = datetime.now().strftime("%Y-%m-%d")
        stem = Path(log_file).stem   # e.g. "ranzer_events"
        self.log_file = str(logs_dir / f"{stem}_{today}.log")

        # Also keep a latest symlink for easy tailing
        latest = logs_dir / f"{stem}_latest.log"
        try:
            if latest.exists() or latest.is_symlink():
                latest.unlink()
            latest.symlink_to(Path(self.log_file).name)
        except OSError:
            pass

    def handle_event(self, event: AnyEvent):
        record = self._to_record(event)
        if not record:
            return
        self._enqueue(record)
        self._write(record)
        self._console(record)
        self._check_escalation(record)

    def handle_assessment(self, assessment: ThreatAssessment):
        if assessment.threat_level == "NONE":
            return
        record = {
            "id": self._id("ASMT"),
            "type": "assessment",
            "severity": assessment.threat_level,
            "threat_score": round(assessment.threat_score, 2),
            "recommended_action": assessment.recommended_action,
            "correlated_pids": assessment.correlated_pids,
            "signal_count": len(assessment.signals),
            "timestamp": assessment.timestamp,
            "time_str": _fmt(assessment.timestamp),
            "description": (f"Threat score={assessment.threat_score:.1f} "
                            f"level={assessment.threat_level} action={assessment.recommended_action}"),
        }
        self._enqueue(record)
        self._write(record)
        self._check_escalation(record)

    def get_alerts(self, limit: int = 100, min_severity: str = None) -> list:
        alerts = self._queue[-limit:]
        if min_severity:
            min_lvl = _SEV.get(min_severity.upper(), 0)
            alerts = [a for a in alerts if _SEV.get(a.get("severity", "LOW"), 0) >= min_lvl]
        return alerts

    def get_alert_counts(self) -> dict:
        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0, "total": 0}
        for a in self._queue:
            sev = a.get("severity", "LOW")
            if sev in counts:
                counts[sev] += 1
            counts["total"] += 1
        return counts

    def export_json(self, path: str):
        with open(path, "w") as f:
            json.dump(self._queue, f, indent=2)

    def export_csv(self, path: str):
        import csv
        keys = ["id", "type", "severity", "description", "time_str", "process_pid"]
        with open(path, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(self._queue)

    def export_txt(self, path: str):
        with open(path, "w") as f:
            f.write("RANZER Alert Export\n" + "=" * 60 + "\n\n")
            for a in self._queue:
                f.write(f"[{a.get('time_str','')}] [{a.get('severity','')}] {a.get('description','')}\n")

    def clear(self):
        self._queue.clear()

    def _to_record(self, event) -> dict:
        try:
            base = event.to_dict()
        except AttributeError:
            return {}
        return {"id": self._id(base.get("type", "EVT")[:4].upper()),
                "description": self._describe(event),
                "time_str": _fmt(base.get("timestamp", time.time())), **base}

    def _describe(self, event) -> str:
        if isinstance(event, EntropyEvent):
            return f"Entropy anomaly in {Path(event.file_path).name} - possible encryption (entropy={event.entropy:.2f})"
        elif isinstance(event, HoneyFileEvent):
            return f"Honey file {event.event_type}: {Path(event.file_path).name} - potential ransomware activity"
        elif isinstance(event, ProcessEvent):
            return f"Suspicious process: {event.process_name} (PID {event.pid}) - {event.event_reason.replace('_', ' ')}"
        return "Unknown detection event"

    def _enqueue(self, record: dict):
        self._queue.append(record)
        if len(self._queue) > self.max_queue_size:
            self._queue = self._queue[-self.max_queue_size:]

    def _check_escalation(self, record: dict):
        """
        Fire at most one notification per escalation step.
        MEDIUM → HIGH → CRITICAL: each level triggers exactly once, no repeats.
        LOW alerts are never notified.

        NOTE: notify-send is gated on enable_desktop_alerts, but escalation_callback
        (GUI popup) always fires regardless - the GUI disables notify-send on launch
        but still needs its own popups.
        """
        sev   = record.get("severity", "LOW").upper()
        level = _SEV.get(sev, 0)
        if level < _SEV.get("MEDIUM", 1):
            return
        if level <= self._max_notified_level:
            return                          # already notified at this level or higher
        self._max_notified_level = level

        _messages = {
            "MEDIUM":   ("RANZER - Medium Threat",    "Suspicious activity detected. Take action."),
            "HIGH":     ("RANZER - HIGH THREAT",      "High-risk activity detected. Immediate action required."),
            "CRITICAL": ("RANZER - CRITICAL THREAT",  "TAKE IMMEDIATE ACTION. Possible active ransomware."),
        }
        title, body = _messages.get(sev, (f"RANZER [{sev}]", record.get("description", "")))
        urgency = "critical" if sev in ("CRITICAL", "HIGH") else "normal"

        # notify-send only when explicitly enabled (CLI mode)
        if self.enable_desktop_alerts:
            self._send_notify(title, body, urgency)

        # GUI popup callback always fires (GUI manages its own display)
        if self.escalation_callback:
            self.escalation_callback(sev, body)

    def reset_notification_state(self):
        """Reset escalation tracking - call when a monitoring session starts."""
        self._max_notified_level = -1

    def _send_notify(self, title: str, body: str, urgency: str = "normal"):
        # Windows: use a non-blocking MessageBox on a background thread so CLI
        # alerts are visible without freezing the main loop.
        import threading
        def _show():
            try:
                import ctypes
                MB_ICONWARNING = 0x30
                MB_ICONERROR   = 0x10
                icon = MB_ICONERROR if urgency == "critical" else MB_ICONWARNING
                ctypes.windll.user32.MessageBoxW(0, body, title, icon)
            except Exception:
                print(f"\n[RANZER ALERT] {title}: {body}\n")
        threading.Thread(target=_show, daemon=True).start()

    def _write(self, record: dict):
        try:
            with open(self.log_file, "a") as f:
                f.write(json.dumps(record) + "\n")
        except OSError:
            pass

    def _console(self, record: dict):
        sev = record.get("severity", "LOW")
        msg = f"[{record.get('time_str','')}] [{sev}] {record.get('description','')}"
        if sev == "CRITICAL":
            logger.critical(msg)
        elif sev == "HIGH":
            logger.error(msg)
        elif sev == "MEDIUM":
            logger.warning(msg)
        else:
            logger.info(msg)

    @staticmethod
    def _id(prefix: str = "ALRT") -> str:
        return f"{prefix}-{int(time.time() * 1000) % 1_000_000:06d}"





def setup_logging(level: int = logging.INFO, log_dir: str = ".") -> str:
    """
    Sets up logging with dated log files inside a logs/ subfolder.
    e.g. logs/ranzer_2026-04-25.log - appends, never overwrites.
    """
    logs_dir = Path(log_dir) / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    today = datetime.now().strftime("%Y-%m-%d")
    log_path = str(logs_dir / f"ranzer_{today}.log")
    # Symlink ranzer_latest.log -> today's file for easy tailing
    latest = logs_dir / "ranzer_latest.log"
    try:
        if latest.exists() or latest.is_symlink():
            latest.unlink()
        latest.symlink_to(f"ranzer_{today}.log")
    except OSError:
        pass
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
        handlers=[logging.StreamHandler(), logging.FileHandler(log_path, mode="a")]
    )
    logging.getLogger("watchdog").setLevel(logging.WARNING)
    return log_path
