#!/usr/bin/env python3
"""
RANZER - Ransomware Simulator (for testing ONLY)
Simulates realistic ransomware behavior across four phases:

  Phase 1 — Encrypt existing files in-place  (triggers on_modified + honey files)
  Phase 2 — Rename encrypted files to .enc   (triggers on_moved  + honey files)
  Phase 3 — Drop ransom note                 (triggers on_created)
  Phase 4 — Create new high-entropy files    (triggers on_created + write rate)

This exercises every RANZER detection path: entropy, honey file engine,
rapid write rate, and process tracking.

WARNING: Phase 1 overwrites existing files in the target directory with random
bytes. Only point this at a throwaway test folder.

Usage:
    python3 simulate_ransomware.py --dir ~/Desktop/ranzer_test
    python3 simulate_ransomware.py --dir ~/Desktop/ranzer_test --files 50 --delay 0.3
    python3 simulate_ransomware.py --dir ~/Desktop/ranzer_test --new-only
"""

import os
import sys
import time
import argparse


# ── helpers ──────────────────────────────────────────────────────────────────

def _write_random(path: str, size_kb: int):
    """Write random (high-entropy) bytes to a file, keeping handle open briefly."""
    with open(path, "wb") as f:
        f.write(os.urandom(size_kb * 1024))
        f.flush()
        time.sleep(0.05)   # hold handle open — helps /proc/fd / psutil detection


def _print(msg: str):
    print(f"[SIM] {msg}", flush=True)


# ── main ─────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="RANZER ransomware simulator — safe test only"
    )
    parser.add_argument("--dir",      required=True,              help="Target directory")
    parser.add_argument("--files",    type=int,   default=50,     help="New files to create in Phase 4 (default 50)")
    parser.add_argument("--delay",    type=float, default=0.3,    help="Delay between operations in seconds (default 0.3)")
    parser.add_argument("--size",     type=int,   default=50,     help="File size in KB (default 50)")
    parser.add_argument("--new-only", action="store_true",        help="Skip Phases 1-3; only create new files (old behaviour)")
    args = parser.parse_args()

    target_dir = os.path.expanduser(args.dir)
    if not os.path.isdir(target_dir):
        _print(f"Directory not found: {target_dir}")
        sys.exit(1)

    _print("============================================")
    _print("RANZER Ransomware Simulator")
    _print("============================================")
    _print(f"Target   : {target_dir}")
    _print(f"New files: {args.files}  |  Delay: {args.delay}s  |  Size: {args.size} KB")
    _print(f"PID      : {os.getpid()}  <- RANZER should terminate this")
    _print(f"Phases   : {'4 (full)' if not args.new_only else '4 only (new files)'}")
    _print("============================================")
    _print("")

    # ── Phase 1: Encrypt existing files in-place ─────────────────────────────
    # Real ransomware opens every file it finds and overwrites the contents.
    # This is the phase that touches honey files and triggers the honey engine.
    if not args.new_only:
        existing = sorted([
            f for f in os.listdir(target_dir)
            if os.path.isfile(os.path.join(target_dir, f))
        ])

        if existing:
            _print(f"Phase 1 — Encrypting {len(existing)} existing file(s) in-place ...")
            for fname in existing:
                fpath = os.path.join(target_dir, fname)
                try:
                    _write_random(fpath, args.size)
                    _print(f"  [encrypted] {fname}")
                except Exception as e:
                    _print(f"  Stopped during Phase 1: {e}")
                    _print(f"  RANZER likely terminated this process.")
                    return
                time.sleep(args.delay)
        else:
            _print("Phase 1 — No existing files to encrypt (skipping)")

        _print("")

        # ── Phase 2: Rename encrypted files ──────────────────────────────────
        # Adds .enc extension — triggers on_moved; also fires honey file renamed event.
        _print("Phase 2 — Renaming encrypted files to .enc ...")
        for fname in existing:
            src = os.path.join(target_dir, fname)
            dst = src + ".enc"
            try:
                if os.path.exists(src):
                    os.rename(src, dst)
                    _print(f"  [renamed] {fname} -> {fname}.enc")
                    time.sleep(0.05)
            except Exception as e:
                _print(f"  Rename failed ({fname}): {e}")

        _print("")

        # ── Phase 3: Drop ransom note ─────────────────────────────────────────
        # Creates a text file — triggers on_created (low entropy, but creates event).
        note_path = os.path.join(target_dir, "README_DECRYPT.txt")
        try:
            with open(note_path, "w") as f:
                f.write(
                    "YOUR FILES HAVE BEEN ENCRYPTED\n\n"
                    "To recover your files, send 1 BTC to...\n\n"
                    "--- RANZER SIMULATOR: THIS IS A SAFE TEST ---\n"
                )
            _print("Phase 3 — Ransom note dropped: README_DECRYPT.txt")
        except Exception as e:
            _print(f"Phase 3 — Note dropped failed: {e}")

        _print("")

    # ── Phase 4: Create new high-entropy files ────────────────────────────────
    # Same as the original simulator — triggers rapid write rate + entropy detection.
    _print(f"Phase 4 — Creating {args.files} new encrypted file(s) ...")
    written = 0
    for i in range(1, args.files + 1):
        fpath = os.path.join(target_dir, f"encrypted_{i:04d}.enc")
        try:
            _write_random(fpath, args.size)
            written += 1
            _print(f"  [{i}/{args.files}] {os.path.basename(fpath)}")
        except Exception as e:
            _print(f"  Stopped at file {i}: {e}")
            _print(f"  RANZER likely terminated this process after {written} new files.")
            return
        time.sleep(args.delay)

    _print("")
    _print(f"Completed — {written} new files written without being terminated.")
    _print("Ensure --auto-terminate is enabled and a directory is being monitored.")


if __name__ == "__main__":
    main()
