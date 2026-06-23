"""
RANZER - Honey File Engine
Deploys realistic decoy files. Any tampering is a high-confidence ransomware trigger.
"""

import os
import time
import json
import random
import hashlib
import logging
from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import Optional

logger = logging.getLogger("ranzer.honeyfile")

DECOY_FILENAMES = [
    "important_notes.txt", "passwords_backup.txt", "financial_report_2024.docx",
    "project_summary.pdf", "client_data.csv", "system_config.cfg",
    "readme_private.txt", "backup_keys.txt", "personal_info.txt", "credentials.txt",
]

DECOY_CONTENTS = [
    "Project Notes\n==============\nLast updated: {date}\n\nKey deliverables:\n- System migration complete\n- Backups verified\nContact: admin@company.local\n",
    "Personal Notes\n==============\n1. Update passwords monthly\n2. Back up important files\n3. Check security alerts\nThis file is monitored.\n",
    "Config Reference\n================\nServer: 192.168.1.100\nPort: 8443\nBackup: Daily 02:00\nRetention: 30 days\n",
    "Financial Summary\n=================\nQ1: $1,245,320\nQ2: $1,389,100\nExpenses: $892,450\nConfidential - Internal Use Only\n",
]


@dataclass
class HoneyFileEvent:
    file_path: str
    event_type: str
    original_hash: str
    current_hash: Optional[str]
    process_pid: Optional[int] = None
    process_name: Optional[str] = None
    timestamp: float = field(default_factory=time.time)

    @property
    def severity(self) -> str:
        if self.event_type in ("deleted", "renamed"):
            return "CRITICAL"
        elif self.event_type == "modified":
            return "HIGH"
        return "MEDIUM"

    def to_dict(self) -> dict:
        return {
            "type": "honeyfile",
            "file_path": self.file_path,
            "event_type": self.event_type,
            "severity": self.severity,
            "original_hash": self.original_hash,
            "current_hash": self.current_hash,
            "process_pid": self.process_pid,
            "process_name": self.process_name,
            "timestamp": self.timestamp,
        }


def _hash_file(file_path: str) -> Optional[str]:
    try:
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(65536), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    except (OSError, IOError):
        return None


class HoneyFileEngine:
    def __init__(self, alert_callback=None):
        self.alert_callback = alert_callback
        self._registry: dict = {}
        self._event_history: list = []

    def deploy(self, directory: str, count: int = 3) -> list:
        directory = str(Path(directory).resolve())
        if not os.path.isdir(directory):
            logger.warning(f"Not a directory: {directory}")
            return []
        deployed = []
        used = set()
        for _ in range(count):
            name = self._pick_name(used)
            used.add(name)
            path = os.path.join(directory, name)
            try:
                content = random.choice(DECOY_CONTENTS).format(date=date.today())
                with open(path, "w") as f:
                    f.write(content)
                h = _hash_file(path)
                if h:
                    self._registry[path] = h
                    deployed.append(path)
                    logger.info(f"[HONEYFILE] Deployed: {path}")
            except (PermissionError, OSError) as e:
                logger.warning(f"Could not deploy {path}: {e}")
        return deployed

    def deploy_to_directories(self, directories: list, count_per_dir: int = 2) -> list:
        all_deployed = []
        for d in directories:
            all_deployed.extend(self.deploy(d, count=count_per_dir))
        return all_deployed

    def remove_all(self):
        for path in list(self._registry.keys()):
            try:
                if os.path.exists(path):
                    os.remove(path)
            except OSError:
                pass
        self._registry.clear()

    def is_honey_file(self, file_path: str) -> bool:
        return str(Path(file_path).resolve()) in self._registry

    def check_file(self, file_path: str, event_type: str = "modified",
                   process_pid: int = None, process_name: str = None) -> Optional[HoneyFileEvent]:
        resolved = str(Path(file_path).resolve())
        if resolved not in self._registry:
            return None
        original_hash = self._registry[resolved]
        current_hash = _hash_file(resolved) if os.path.exists(resolved) else None
        if event_type == "modified" and current_hash == original_hash:
            return None
        event = HoneyFileEvent(
            file_path=resolved, event_type=event_type,
            original_hash=original_hash, current_hash=current_hash,
            process_pid=process_pid, process_name=process_name,
        )
        self._event_history.append(event)
        logger.warning(f"[HONEYFILE] {event.severity} | {event_type} on {resolved}")
        if self.alert_callback:
            self.alert_callback(event)
        return event

    def scan_all(self) -> list:
        events = []
        for path, original_hash in list(self._registry.items()):
            if not os.path.exists(path):
                e = self.check_file(path, event_type="deleted")
            else:
                e = self.check_file(path, event_type="modified") if _hash_file(path) != original_hash else None
            if e:
                events.append(e)
        return events

    def save_state(self, state_file: str):
        try:
            with open(state_file, "w") as f:
                json.dump(self._registry, f, indent=2)
        except OSError as e:
            logger.error(f"Could not save honey state: {e}")

    def load_state(self, state_file: str):
        try:
            with open(state_file, "r") as f:
                self._registry = json.load(f)
        except (OSError, json.JSONDecodeError):
            pass

    def get_registered_paths(self) -> list:
        return list(self._registry.keys())

    def get_recent_events(self, limit: int = 50) -> list:
        return self._event_history[-limit:]

    def clear_history(self):
        self._event_history.clear()

    def _pick_name(self, used: set) -> str:
        available = [n for n in DECOY_FILENAMES if n not in used]
        if available:
            return random.choice(available)
        base = random.choice(DECOY_FILENAMES)
        stem, ext = os.path.splitext(base)
        return f"{stem}_{random.randint(1000,9999)}{ext}"
