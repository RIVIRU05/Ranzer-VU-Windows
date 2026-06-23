#!/usr/bin/env python3
"""
RANZER - Low Risk Process Simulator
Writes low-entropy files continuously — detectable by the process tracker
(write rate > 100 KB/s) but entropy stays well below the threshold so no
entropy alerts fire and the threat score never reaches CRITICAL.

The process runs indefinitely until manually terminated from the
RANZER GUI System Actions page or via Ctrl+C.

Usage:
    python3 simulate_risk_low.py --dir ~/Desktop/ranzer_test
    python3 simulate_risk_low.py --dir ~/Desktop/ranzer_test --delay 0.3 --size 150
"""

import os
import sys
import time
import signal
import argparse


def _low_entropy_block(size_bytes: int) -> bytes:
    """Repeating ASCII pattern — entropy ~1.5, well below the 7.5 threshold."""
    pattern = b"RANZER_LOWRISK_TESTDATA_" * (size_bytes // 24 + 1)
    return pattern[:size_bytes]


def main():
    parser = argparse.ArgumentParser(
        description="RANZER low-risk simulator — tests manual termination via GUI"
    )
    parser.add_argument("--dir",   required=True,           help="Directory to write files into")
    parser.add_argument("--delay", type=float, default=0.4, help="Delay between files in seconds (default 0.4)")
    parser.add_argument("--size",  type=int,   default=120, help="File size in KB (default 120)")
    args = parser.parse_args()

    target_dir = os.path.expanduser(args.dir)
    if not os.path.isdir(target_dir):
        print(f"[!] Directory not found: {target_dir}")
        sys.exit(1)

    print("[LOW-RISK] ============================================")
    print("[LOW-RISK] RANZER Low-Risk Process Simulator")
    print("[LOW-RISK] ============================================")
    print(f"[LOW-RISK] Target : {target_dir}")
    print(f"[LOW-RISK] Delay  : {args.delay}s between files")
    print(f"[LOW-RISK] Size   : {args.size} KB per file  (low entropy — no entropy alerts)")
    print(f"[LOW-RISK] PID    : {os.getpid()}")
    print("[LOW-RISK] ============================================")
    print("[LOW-RISK] Running until manually terminated from RANZER GUI.")
    print()

    running = True

    def _handle_signal(sig, frame):
        nonlocal running
        running = False
        print(f"\n[LOW-RISK] Received termination signal — stopping (PID {os.getpid()})")

    signal.signal(signal.SIGTERM, _handle_signal)
    signal.signal(signal.SIGINT,  _handle_signal)

    i = 0
    while running:
        i += 1
        filename = os.path.join(target_dir, f"lowrisk_{i:04d}.tmp")
        try:
            data = _low_entropy_block(args.size * 1024)
            with open(filename, "wb") as f:
                f.write(data)
                f.flush()
                time.sleep(0.05)
            print(f"[LOW-RISK] Written ({i}): {os.path.basename(filename)}")
        except Exception as e:
            print(f"[LOW-RISK] Stopped: {e}")
            return
        time.sleep(args.delay)

    print(f"[LOW-RISK] Process ended cleanly (PID {os.getpid()})")


if __name__ == "__main__":
    main()
