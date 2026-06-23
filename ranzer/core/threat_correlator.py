"""
RANZER - Threat Correlation Engine
Combines entropy, honey file, and process signals into a unified threat score.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Union

from .entropy_monitor import EntropyEvent
from .honey_file_engine import HoneyFileEvent
from .process_tracker import ProcessEvent

logger = logging.getLogger("ranzer.correlator")

AnyEvent = Union[EntropyEvent, HoneyFileEvent, ProcessEvent]

_SEVERITY_SCORES = {"CRITICAL": 40, "HIGH": 25, "MEDIUM": 15, "LOW": 5}
_TYPE_MULTIPLIERS = {"honeyfile": 1.5, "entropy": 1.0, "process": 1.2}


@dataclass
class ThreatAssessment:
    threat_score: float
    threat_level: str
    signals: list
    recommended_action: str
    correlated_pids: list
    correlated_files: list
    timestamp: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "threat_score": round(self.threat_score, 2),
            "threat_level": self.threat_level,
            "recommended_action": self.recommended_action,
            "correlated_pids": self.correlated_pids,
            "correlated_files": self.correlated_files[:10],
            "signal_count": len(self.signals),
            "timestamp": self.timestamp,
        }


class ThreatCorrelator:
    THRESHOLDS = {"LOW": 20, "MEDIUM": 40, "HIGH": 65, "CRITICAL": 90}
    ACTIONS = {"NONE": "MONITOR", "LOW": "MONITOR",
               "MEDIUM": "ALERT", "HIGH": "ALERT", "CRITICAL": "TERMINATE"}

    def __init__(self, decay_window: float = 30.0, auto_action_callback=None):
        self.decay_window = decay_window
        self.auto_action_callback = auto_action_callback
        self._signals: list = []
        self._assessments: list = []

    def ingest(self, event: AnyEvent) -> ThreatAssessment:
        self._signals.append((time.time(), event))
        self._prune()
        assessment = self._assess()
        self._assessments.append(assessment)
        logger.info(f"[CORRELATOR] score={assessment.threat_score:.1f} level={assessment.threat_level}")
        if assessment.threat_level in ("HIGH", "CRITICAL") and self.auto_action_callback:
            self.auto_action_callback(assessment)
        return assessment

    def _assess(self) -> ThreatAssessment:
        now = time.time()
        total_score = 0.0
        signal_dicts = []
        pids: set = set()
        files: set = set()

        for ts, event in self._signals:
            decay = max(0.1, 1.0 - ((now - ts) / (self.decay_window * 2)))
            base = _SEVERITY_SCORES.get(event.severity, 5)
            etype = self._etype(event)
            total_score += base * _TYPE_MULTIPLIERS.get(etype, 1.0) * decay
            signal_dicts.append(event.to_dict())
            pid = getattr(event, "process_pid", None) or getattr(event, "pid", None)
            if pid:
                pids.add(pid)
            if hasattr(event, "file_path"):
                files.add(event.file_path)

        # Cross-signal bonus: same PID in multiple engine types
        pid_types: dict = {}
        for _, event in self._signals:
            pid = getattr(event, "process_pid", None) or getattr(event, "pid", None)
            if pid:
                pid_types.setdefault(pid, set()).add(self._etype(event))
        for types in pid_types.values():
            if len(types) > 1:
                total_score += 10 * (len(types) - 1)

        level = self._level(total_score)
        return ThreatAssessment(
            threat_score=total_score, threat_level=level,
            signals=signal_dicts, recommended_action=self.ACTIONS.get(level, "MONITOR"),
            correlated_pids=list(pids), correlated_files=list(files),
        )

    def _prune(self, max_age: float = 120.0):
        cutoff = time.time() - max_age
        self._signals = [(ts, ev) for ts, ev in self._signals if ts > cutoff]

    def _level(self, score: float) -> str:
        if score >= self.THRESHOLDS["CRITICAL"]:
            return "CRITICAL"
        elif score >= self.THRESHOLDS["HIGH"]:
            return "HIGH"
        elif score >= self.THRESHOLDS["MEDIUM"]:
            return "MEDIUM"
        elif score >= self.THRESHOLDS["LOW"]:
            return "LOW"
        return "NONE"

    @staticmethod
    def _etype(event: AnyEvent) -> str:
        if isinstance(event, EntropyEvent):
            return "entropy"
        elif isinstance(event, HoneyFileEvent):
            return "honeyfile"
        elif isinstance(event, ProcessEvent):
            return "process"
        return "unknown"

    def get_latest_assessment(self):
        return self._assessments[-1] if self._assessments else None

    def reset(self):
        self._signals.clear()
        self._assessments.clear()
