#!/usr/bin/env python3
"""
scripts/build-windows-events.py
CLI wrapper around core.kb.sync.sync_windows_events_and_evtx.
Compiles authoritative Windows Event IDs and Expanded EVTX channel definitions into data/windows-events.json.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.kb.sync import sync_windows_events_and_evtx
from core.config import WIN_EVENTS_DB_PATH


def main():
    parser = argparse.ArgumentParser(description="Compile Windows Event Log forensic intelligence dataset.")
    parser.add_argument("-o", "--output", default=str(WIN_EVENTS_DB_PATH), help="Target JSON destination path")
    parser.add_argument("-v", "--verbose", action="store_true", default=True, help="Enable verbose logging")
    args = parser.parse_args()

    count = sync_windows_events_and_evtx(output_path=Path(args.output), verbose=args.verbose)
    if count > 0:
        print(f"[SUCCESS] Compiled {count} Windows Event & EVTX records into {args.output}")
        sys.exit(0)
    else:
        print(f"[ERROR] Failed to compile Windows Event & EVTX dataset.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
