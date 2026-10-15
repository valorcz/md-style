#!/usr/bin/env python3
"""
scripts/build-mitre-dataset.py
CLI wrapper around core.kb.sync.sync_mitre_attack.
Fetches canonical MITRE ATT&CK Enterprise Matrix from official MITRE CTI STIX repository.
"""

import argparse
import sys
from pathlib import Path

# Add project root to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from core.kb.sync import sync_mitre_attack, DEFAULT_MITRE_STIX_URL
from core.config import MITRE_DB_PATH


def main():
    parser = argparse.ArgumentParser(description="Fetch and compile the canonical MITRE ATT&CK Enterprise Matrix.")
    parser.add_argument("-s", "--source", default=DEFAULT_MITRE_STIX_URL, help="URL to official MITRE STIX JSON")
    parser.add_argument("-o", "--output", default=str(MITRE_DB_PATH), help="Target JSON destination path")
    parser.add_argument("-v", "--verbose", action="store_true", default=True, help="Enable verbose debug output")
    args = parser.parse_args()

    count = sync_mitre_attack(source_url=args.source, output_path=Path(args.output), verbose=args.verbose)
    if count > 0:
        print(f"[SUCCESS] Compiled {count} MITRE techniques into {args.output}")
        sys.exit(0)
    else:
        print(f"[ERROR] Failed to compile MITRE techniques.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
