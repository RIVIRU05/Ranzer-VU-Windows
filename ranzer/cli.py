#!/usr/bin/env python3
"""
RANZER CLI — Windows
Usage:
  python -m ranzer.cli start --dirs C:\\Users\\you\\Documents
  python -m ranzer.cli status
  python -m ranzer.cli log [--limit 20] [--severity HIGH]
  python -m ranzer.cli scan --file C:\\path\\to\\file
  python -m ranzer.cli export --format json --output alerts.json
"""

import argparse
import json
import os
import sys
import signal
import time
from datetime import datetime

from ranzer.core import RanzerEngine, RanzerConfig, calculate_shannon_entropy

_TEMP = os.environ.get("TEMP", os.environ.get("TMP", os.path.expanduser("~")))
PID_FILE   = os.path.join(_TEMP, "ranzer.pid")
STATE_FILE = os.path.join(_TEMP, "ranzer_state.json")


def _write_state(mode: str, dirs: list, config: RanzerConfig, log_dir: str = None):
    state = {
        "pid": os.getpid(),
        "mode": mode,
        "start_time": datetime.now().isoformat(),
        "dirs": dirs,
        "entropy_threshold": config.entropy_threshold,
        "honey_files": config.enable_honey_files,
        "auto_terminate": config.enable_auto_terminate,
        "log_dir": log_dir or os.path.abspath(config.log_dir),
    }
    try:
        with open(STATE_FILE, "w") as f:
            json.dump(state, f)
    except OSError:
        pass


def _clear_state():
    for path in (STATE_FILE, PID_FILE):
        try:
            os.remove(path)
        except FileNotFoundError:
            pass


def cmd_start(args):
    dirs = [d.strip() for d in args.dirs.split(",") if d.strip()] if args.dirs else []
    if not dirs:
        print("[!] No directories specified. Use --dirs C:\\path\\to\\dir")
        sys.exit(1)
    for d in dirs:
        if not os.path.isdir(d):
            print(f"[!] Not a directory: {d}")
            sys.exit(1)

    config = RanzerConfig(
        monitored_dirs=dirs,
        entropy_threshold=args.threshold,
        enable_honey_files=not args.no_honeyfiles,
        enable_auto_terminate=args.auto_terminate,
        enable_desktop_alerts=not args.no_desktop,
    )
    engine = RanzerEngine(config)
    engine.start()
    _write_state("cli", dirs, config)
    with open(PID_FILE, "w") as f:
        f.write(str(os.getpid()))

    print(f"[*] RANZER started — monitoring: {', '.join(dirs)}")
    print(f"[*] Entropy threshold : {args.threshold}")
    print(f"[*] Honey files       : {'enabled' if not args.no_honeyfiles else 'disabled'}")
    print(f"[*] Auto-terminate    : {'enabled' if args.auto_terminate else 'disabled'}")
    print("[*] Press Ctrl+C to stop.\n")

    def _stop(sig, frame):
        print("\n[*] Stopping RANZER...")
        engine.stop()
        _clear_state()
        sys.exit(0)

    signal.signal(signal.SIGINT, _stop)
    # Windows does not deliver SIGTERM the same way, but register it for completeness
    try:
        signal.signal(signal.SIGTERM, _stop)
    except (OSError, ValueError):
        pass

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        _stop(None, None)


def cmd_status(args):
    import psutil

    state = None
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
        except Exception:
            pass

    pid_str = None
    if state:
        pid_str = str(state.get("pid", ""))
    elif os.path.exists(PID_FILE):
        with open(PID_FILE) as f:
            pid_str = f.read().strip()

    if not pid_str:
        print("[ ] RANZER is not running.")
        return

    try:
        proc = psutil.Process(int(pid_str))
        mode = state.get("mode", "cli").upper() if state else "CLI"
        print(f"[*] RANZER is running  (PID {pid_str})  [{mode} mode]")
        print()

        if state:
            start = datetime.fromisoformat(state["start_time"])
            delta = int((datetime.now() - start).total_seconds())
            h, rem = divmod(delta, 3600)
            m, s = divmod(rem, 60)
            uptime_str = f"{h}h {m}m {s}s" if h else f"{m}m {s}s"
            dirs = state.get("dirs", [])
            print(f"    Uptime       : {uptime_str}")
            print(f"    Directories  : {', '.join(dirs) if dirs else '(none)'}")
            print(f"    Threshold    : {state.get('entropy_threshold', 7.5)}")
            print(f"    Honey files  : {'enabled' if state.get('honey_files') else 'disabled'}")
            print(f"    Auto-term    : {'enabled' if state.get('auto_terminate') else 'disabled'}")
            print()

        cpu = proc.cpu_percent(interval=0.3)
        mem = proc.memory_info().rss / 1024 / 1024
        threads = proc.num_threads()
        print(f"    CPU          : {cpu:.1f}%")
        print(f"    Memory       : {mem:.1f} MB")
        print(f"    Threads      : {threads}")
        print()

        counts = {"CRITICAL": 0, "HIGH": 0, "MEDIUM": 0, "LOW": 0}
        log_candidates = [
            os.path.join("logs", "ranzer_events_latest.log"),
            "ranzer_events.log",
        ]
        for log_path in log_candidates:
            if os.path.exists(log_path):
                with open(log_path) as f:
                    for line in f:
                        try:
                            r = json.loads(line.strip())
                            sev = r.get("severity", "").upper()
                            if sev in counts:
                                counts[sev] += 1
                        except Exception:
                            continue
                break
        total = sum(counts.values())
        print(f"    Alerts       : {total} total  "
              f"({counts['CRITICAL']} critical, {counts['HIGH']} high, "
              f"{counts['MEDIUM']} medium, {counts['LOW']} low)")

    except psutil.NoSuchProcess:
        print(f"[!] PID {pid_str} not found — RANZER may have stopped unexpectedly.")
        _clear_state()
    except Exception as e:
        print(f"[!] Error reading process info: {e}")


def _resolve_log_file() -> str:
    candidates = []
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                state = json.load(f)
            log_dir = state.get("log_dir", ".")
            candidates.append(os.path.join(log_dir, "logs", "ranzer_events_latest.log"))
        except Exception:
            pass
    candidates += [
        os.path.join("logs", "ranzer_events_latest.log"),
        "ranzer_events.log",
    ]
    for c in candidates:
        if os.path.isfile(c):
            return c
    return ""


def cmd_log(args):
    log_file = _resolve_log_file()
    if not log_file:
        print("[!] No event log found. Has RANZER been started yet?")
        return
    sev_order = {"LOW": 0, "MEDIUM": 1, "HIGH": 2, "CRITICAL": 3}
    min_level = sev_order.get(args.severity.upper(), 0) if args.severity else 0
    lines = []
    with open(log_file) as f:
        for line in f:
            try:
                r = json.loads(line.strip())
                if sev_order.get(r.get("severity", "LOW"), 0) >= min_level:
                    lines.append(r)
            except json.JSONDecodeError:
                continue
    for r in lines[-args.limit:]:
        pid = r.get("process_pid") or r.get("pid") or ""
        pid_str = f" | PID {pid}" if pid else ""
        print(f"[{r.get('time_str','')}] [{r.get('severity','?')}]{pid_str} {r.get('description','')}")
    if not lines:
        print("[*] No matching events found.")


def cmd_scan(args):
    if not os.path.isfile(args.file):
        print(f"[!] File not found: {args.file}")
        sys.exit(1)
    with open(args.file, "rb") as f:
        data = f.read(10 * 1024 * 1024)
    entropy = calculate_shannon_entropy(data)
    status = "HIGH ENTROPY — likely encrypted" if entropy > args.threshold else "Normal"
    print(f"File    : {args.file}")
    print(f"Entropy : {entropy:.4f} / 8.0")
    print(f"Status  : {status} (threshold: {args.threshold})")


def cmd_export(args):
    log_file = _resolve_log_file()
    if not log_file:
        print("[!] No event log to export.")
        return
    records = []
    with open(log_file) as f:
        for line in f:
            try:
                records.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
    output = args.output or f"ranzer_export.{args.format}"
    fmt = args.format.lower()
    if fmt == "json":
        with open(output, "w") as f:
            json.dump(records, f, indent=2)
    elif fmt == "csv":
        import csv
        keys = ["id", "type", "severity", "description", "time_str", "process_pid"]
        with open(output, "w", newline="") as f:
            w = csv.DictWriter(f, fieldnames=keys, extrasaction="ignore")
            w.writeheader()
            w.writerows(records)
    elif fmt == "txt":
        with open(output, "w") as f:
            for r in records:
                f.write(f"[{r.get('time_str','')}] [{r.get('severity','')}] {r.get('description','')}\n")
    print(f"[*] Exported {len(records)} events to {output}")


def cmd_gui(args):
    from ranzer.gui.app import launch_gui
    dirs = [d.strip() for d in args.dirs.split(",") if d.strip()] if args.dirs else []
    launch_gui(prefill_dirs=dirs)


def main():
    parser = argparse.ArgumentParser(prog="ranzer",
                                     description="RANZER — Ransomware Analyzer EPS")
    sub = parser.add_subparsers(dest="command")

    p = sub.add_parser("start", help="Start monitoring")
    p.add_argument("--dirs", required=True,
                   help="Comma-separated directories to monitor")
    p.add_argument("--threshold", type=float, default=7.5,
                   help="Entropy threshold (default 7.5)")
    p.add_argument("--no-honeyfiles", action="store_true")
    p.add_argument("--auto-terminate", action="store_true")
    p.add_argument("--no-desktop", action="store_true")

    sub.add_parser("status", help="Check if RANZER is running")

    p = sub.add_parser("log", help="View recent alerts")
    p.add_argument("--limit", type=int, default=20)
    p.add_argument("--severity", help="MIN severity: LOW|MEDIUM|HIGH|CRITICAL")

    p = sub.add_parser("scan", help="One-shot entropy scan of a file")
    p.add_argument("--file", required=True)
    p.add_argument("--threshold", type=float, default=7.5)

    p = sub.add_parser("export", help="Export alert log")
    p.add_argument("--format", choices=["json", "csv", "txt"], default="json")
    p.add_argument("--output", help="Output file path")

    p = sub.add_parser("gui", help="Launch the graphical interface")
    p.add_argument("--dirs", help="Comma-separated directories to pre-fill", default="")

    args = parser.parse_args()
    if args.command == "start":
        cmd_start(args)
    elif args.command == "status":
        cmd_status(args)
    elif args.command == "log":
        cmd_log(args)
    elif args.command == "scan":
        cmd_scan(args)
    elif args.command == "export":
        cmd_export(args)
    elif args.command == "gui":
        cmd_gui(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
