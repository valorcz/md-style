#!/usr/bin/env python3
"""
scripts/build-cwe-dataset.py
CLI wrapper around core.kb.sync.sync_cwe_catalog.
Downloads official canonical MITRE CWE XML release, correlates ATT&CK techniques,
and compiles data/cwe.json.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.kb.sync import sync_cwe_catalog
from core.config import CWE_DB_PATH, DEFAULT_MITRE_CWE_URL


def main():
    parser = argparse.ArgumentParser(description="Fetch and compile the canonical MITRE CWE catalog.")
    parser.add_argument("-s", "--source", default=DEFAULT_MITRE_CWE_URL, help="URL to official MITRE CWE XML ZIP archive")
    parser.add_argument("-o", "--output", default=str(CWE_DB_PATH), help="Target JSON destination path")
    parser.add_argument("-v", "--verbose", action="store_true", default=True, help="Enable verbose debug output")
    args = parser.parse_args()

    count = sync_cwe_catalog(source_url=args.source, output_path=Path(args.output), verbose=args.verbose)
    if count > 0:
        print(f"[SUCCESS] Compiled {count} CWE records into {args.output}")
        sys.exit(0)
    else:
        print(f"[ERROR] Failed to compile CWE dataset.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
