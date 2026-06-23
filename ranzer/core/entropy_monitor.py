"""
RANZER - Entropy Monitor Engine
Computes Shannon entropy for files and flags anomalies above threshold.
Encrypted files exhibit entropy close to 8.0 (maximum randomness).
"""

import math
import os
import time
import logging
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ranzer.entropy")

HIGH_ENTROPY_EXTENSIONS = {
    ".zip", ".gz", ".bz2", ".xz", ".7z", ".rar", ".tar",
    ".jpg", ".jpeg", ".png", ".gif", ".webp",
    ".mp3", ".mp4", ".mkv", ".avi", ".mov", ".flac", ".ogg", ".pdf",
}


@dataclass
class EntropyEvent:
    file_path: str
    entropy: float
    threshold: float
    file_size: int
    timestamp: float = field(default_factory=time.time)
    process_pid: Optional[int] = None
    process_name: Optional[str] = None

    @property
    def severity(self) -> str:
        delta = self.entropy - self.threshold
        if delta >= 0.4:
            return "CRITICAL"
        elif delta >= 0.2:
            return "HIGH"
        elif delta >= 0.0:
            return "MEDIUM"
        return "LOW"

    def to_dict(self) -> dict:
        return {
            "type": "entropy",
            "file_path": self.file_path,
            "entropy": round(self.entropy, 4),
            "threshold": self.threshold,
            "file_size": self.file_size,
            "severity": self.severity,
            "timestamp": self.timestamp,
            "process_pid": self.process_pid,
            "process_name": self.process_name,
        }


def calculate_shannon_entropy(data: bytes) -> float:
    if not data:
        return 0.0
    freq = Counter(data)
    total = len(data)
    entropy = 0.0
    for count in freq.values():
        p = count / total
        entropy -= p * math.log2(p)
    return entropy


def calculate_file_entropy(file_path: str, max_bytes: int = 10 * 1024 * 1024) -> Optional[float]:
    try:
        path = Path(file_path)
        if not path.exists() or not path.is_file():
            return None
        if path.stat().st_size == 0:
            return 0.0
        with open(path, "rb") as f:
            data = f.read(max_bytes)
        return calculate_shannon_entropy(data)
    except (PermissionError, OSError):
        return None


class EntropyMonitor:
    def __init__(self, threshold: float = 7.5, max_file_size: int = 10 * 1024 * 1024,
                 skip_known_high_entropy: bool = True, alert_callback=None):
        self.threshold = threshold
        self.max_file_size = max_file_size
        self.skip_known_high_entropy = skip_known_high_entropy
        self.alert_callback = alert_callback
        self._event_history = []

    def analyze_file(self, file_path: str, process_pid: int = None,
                     process_name: str = None) -> Optional[EntropyEvent]:
        if self.skip_known_high_entropy:
            if Path(file_path).suffix.lower() in HIGH_ENTROPY_EXTENSIONS:
                return None
        try:
            file_size = Path(file_path).stat().st_size
        except OSError:
            return None
        if file_size > self.max_file_size:
            return None
        entropy = calculate_file_entropy(file_path, self.max_file_size)
        if entropy is None:
            return None
        if entropy > self.threshold:
            event = EntropyEvent(
                file_path=file_path, entropy=entropy,
                threshold=self.threshold, file_size=file_size,
                process_pid=process_pid, process_name=process_name,
            )
            self._event_history.append(event)
            logger.warning(f"[ENTROPY] {event.severity} | {file_path} | entropy={entropy:.4f}")
            if self.alert_callback:
                self.alert_callback(event)
            return event
        return None

    def set_threshold(self, threshold: float):
        if not (0.0 < threshold <= 8.0):
            raise ValueError("Threshold must be between 0.0 and 8.0")
        self.threshold = threshold

    def get_recent_events(self, limit: int = 50) -> list:
        return self._event_history[-limit:]

    def clear_history(self):
        self._event_history.clear()
