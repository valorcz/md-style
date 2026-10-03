#!/usr/bin/env python3
"""
scripts/build-mitre-dataset.py
Fetches and compiles the canonical MITRE ATT&CK Enterprise Matrix from the
official MITRE CTI repository (STIX 2.1) into a lightweight, offline JSON knowledge base.

Source: https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json
Output: data/mitre-attack.json
"""

import argparse
import json
import os
import re
import sys
import time
import urllib.request

DEFAULT_STIX_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
DEFAULT_OUTPUT = os.path.join(PROJECT_DIR, "data", "mitre-attack.json")


def clean_description(raw_text: str, max_chars: int = 320) -> str:
    if not raw_text:
        return "MITRE ATT&CK enterprise adversary technique."
    # Strip markdown citation links e.g. (Citation: ...)
    cleaned = re.sub(r'\(Citation:[^\)]+\)', '', raw_text)
    # Strip markdown hyperlinks e.g. [text](url) -> text
    cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
    # Strip markdown headers or code fences
    cleaned = re.sub(r'[`#*]', '', cleaned)
    # Normalize whitespaces
    cleaned = ' '.join(cleaned.split())
    if len(cleaned) > max_chars:
        return cleaned[:max_chars].rstrip() + "..."
    return cleaned


def build_mitre_dataset(source_url: str = DEFAULT_STIX_URL, output_path: str = DEFAULT_OUTPUT, verbose: bool = False):
    print(f"[MITRE BUILDER] Initiating fetch from official MITRE CTI repository:")
    print(f"  Source: {source_url}")
    print(f"  Target: {output_path}")

    t0 = time.time()
    req = urllib.request.Request(
        source_url,
        headers={"User-Agent": "Antigravity-Security-Tooling/1.0 (Enterprise ATT&CK Compiler)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw_bytes = resp.read()
    except Exception as err:
        print(f"[ERROR] Failed to fetch MITRE CTI STIX repository: {err}", file=sys.stderr)
        if os.path.exists(output_path):
            print(f"[INFO] Existing {output_path} preserved.", file=sys.stderr)
            return 0
        return 1

    download_time = time.time() - t0
    size_mb = len(raw_bytes) / (1024 * 1024)
    print(f"[MITRE BUILDER] Downloaded {size_mb:.1f} MB in {download_time:.2f}s. Parsing STIX objects...")

    t1 = time.time()
    try:
        stix = json.loads(raw_bytes.decode('utf-8'))
    except Exception as err:
        print(f"[ERROR] Failed to parse STIX JSON: {err}", file=sys.stderr)
        return 1

    objects = stix.get("objects", [])
    if verbose:
        print(f"[DEBUG] Total STIX objects parsed: {len(objects)}")

    dataset = {}
    techniques_count = 0
    tactics_count = 0

    for obj in objects:
        if obj.get("revoked") or obj.get("x_mitre_deprecated"):
            continue

        obj_type = obj.get("type")

        # 1. Techniques & Sub-techniques (attack-pattern)
        if obj_type == "attack-pattern":
            ext_refs = obj.get("external_references", [])
            technique_id = None
            technique_url = None

            for ref in ext_refs:
                if ref.get("source_name") == "mitre-attack":
                    technique_id = ref.get("external_id")
                    technique_url = ref.get("url")
                    break

            if technique_id:
                name = obj.get("name", "")
                raw_desc = obj.get("description", "")
                summary = clean_description(raw_desc)

                tactics = [
                    kc.get("phase_name", "").replace("-", " ")
                    for kc in obj.get("kill_chain_phases", [])
                    if kc.get("kill_chain_name") == "mitre-attack"
                ]
                platforms = obj.get("x_mitre_platforms", [])

                dataset[technique_id] = {
                    "type": "mitre",
                    "id": technique_id,
                    "name": name,
                    "summary": summary,
                    "tactics": tactics,
                    "platforms": platforms,
                    "url": technique_url or f"https://attack.mitre.org/techniques/{technique_id.replace('.', '/')}/"
                }
                techniques_count += 1

        # 2. Enterprise Tactics (x-mitre-tactic)
        elif obj_type == "x-mitre-tactic":
            ext_refs = obj.get("external_references", [])
            tactic_id = None
            tactic_url = None

            for ref in ext_refs:
                if ref.get("source_name") == "mitre-attack":
                    tactic_id = ref.get("external_id")
                    tactic_url = ref.get("url")
                    break

            if tactic_id:
                name = obj.get("name", "")
                raw_desc = obj.get("description", "")
                summary = clean_description(raw_desc, max_chars=250)

                dataset[tactic_id] = {
                    "type": "mitre-tactic",
                    "id": tactic_id,
                    "name": name,
                    "summary": summary,
                    "url": tactic_url or f"https://attack.mitre.org/tactics/{tactic_id}/"
                }
                tactics_count += 1

    parse_time = time.time() - t1
    print(f"[MITRE BUILDER] Extracted {techniques_count} techniques and {tactics_count} tactics in {parse_time:.2f}s.")

    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(dataset, f, indent=2, ensure_ascii=False)

    out_kb = os.path.getsize(output_path) / 1024
    total_time = time.time() - t0
    print(f"[SUCCESS] Compiled {len(dataset)} MITRE intelligence records -> {output_path} ({out_kb:.1f} KB) in {total_time:.2f}s.")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Fetch and compile the canonical MITRE ATT&CK Enterprise Matrix.")
    parser.add_argument("-s", "--source", default=DEFAULT_STIX_URL, help="URL to official MITRE STIX JSON")
    parser.add_argument("-o", "--output", default=DEFAULT_OUTPUT, help="Target JSON destination path")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose debug output")
    args = parser.parse_args()

    sys.exit(build_mitre_dataset(args.source, args.output, args.verbose))


if __name__ == "__main__":
    main()
