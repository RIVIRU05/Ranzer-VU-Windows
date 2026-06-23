#!/usr/bin/env python3
"""
RANZER - Ransomware Simulator (for testing ONLY)
Simulates ransomware by rapidly creating high-entropy encrypted-looking files.

Key behavior that matches real ransomware:
- Creates NEW files (triggers on_created, not just on_modified)
- Writes random bytes (maximum entropy ~8.0)
- Keeps file handle open during write (so /proc/fd catches the PID)
- Writes many files rapidly (triggers rate detection)

Usage:
    python3 simulate_ransomware.py --dir ~/Desktop/ranzer_test
    python3 simulate_ransomware.py --dir ~/Desktop/ranzer_test --files 50 --delay 0.3
"""

import os
import sys
import time
import argparse


def main():
    parser = argparse.ArgumentParser(description="RANZER ransomware simulator (safe testing only)")
    parser.add_argument("--dir", required=True, help="Directory to write files into")
    parser.add_argument("--files", type=int, default=50, help="Number of files to write (default 50)")
    parser.add_argument("--delay", type=float, default=0.3, help="Delay between files in seconds (default 0.3)")
    parser.add_argument("--size", type=int, default=50, help="File size in KB (default 50)")
    args = parser.parse_args()

    target_dir = os.path.expanduser(args.dir)
    if not os.path.isdir(target_dir):
        print(f"[!] Directory not found: {target_dir}")
        sys.exit(1)

    print(f"[SIM] ============================================")
    print(f"[SIM] RANZER Ransomware Simulator")
    print(f"[SIM] ============================================")
    print(f"[SIM] Target : {target_dir}")
    print(f"[SIM] Files  : {args.files}")
    print(f"[SIM] Delay  : {args.delay}s between files")
    print(f"[SIM] Size   : {args.size} KB per file")
    print(f"[SIM] PID    : {os.getpid()}  ← RANZER should terminate this")
    print(f"[SIM] ============================================")
    print()

    written = 0
    for i in range(1, args.files + 1):
        filename = os.path.join(target_dir, f"encrypted_{i:04d}.enc")
        try:
            # Keep file open while writing so /proc/fd scan catches this PID
            with open(filename, "wb") as f:
                data = os.urandom(args.size * 1024)
                f.write(data)
                f.flush()
                # Small pause while file is still open — this is when /proc/fd is scanned
                time.sleep(0.05)
            written += 1
            print(f"[SIM] Written ({i}/{args.files}): {os.path.basename(filename)}")
        except Exception as e:
            print(f"[SIM] Stopped: {e}")
            print(f"[SIM] RANZER likely terminated this process after writing {written} files.")
            return

        time.sleep(args.delay)

    print(f"\n[SIM] Completed — wrote {written} files without being terminated.")
    print("[SIM] Make sure --auto-terminate is enabled and entropy threshold is correct.")


if __name__ == "__main__":
    main()
