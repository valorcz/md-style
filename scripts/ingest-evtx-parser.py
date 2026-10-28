#!/usr/bin/env python3
"""
scripts/ingest-evtx-parser.py
Ingests high-fidelity Windows event intelligence from the Cyber-Experts/evtx-parser repository
(https://github.com/Cyber-Experts/evtx-parser) and merges it into data/windows-events.json.

Enriches each event with:
- Concrete investigation tips (investigation_tips)
- Adversary tradecraft and behavior (attacker_behavior)
- Benign causes / False positives (benign_causes)
- MITRE ATT&CK techniques
- Key audit fields
- evtxparser.com & Microsoft reference URLs

Supports local source path or automatic clone/sparse-checkout of the repository.
"""

import argparse
import glob
import json
import os
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Dict, Any, List

try:
    import yaml
except ImportError:
    print("Error: pyyaml is required. Install via `uv add pyyaml` or `pip install pyyaml`.")
    sys.exit(1)

SCRIPT_DIR = Path(__file__).resolve().parent
PROJECT_DIR = SCRIPT_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
TARGET_JSON = DATA_DIR / "windows-events.json"

CHANNEL_CANONICAL_NAMES = {
    "defender": {
        "channel_str": "Microsoft-Windows-Windows Defender/Operational",
        "evtx_files": ["Defender.evtx", "Microsoft-Windows-Windows Defender/Operational.evtx"],
        "category": "Antivirus Protection State / Defense Evasion"
    },
    "rdp-local-session-manager": {
        "channel_str": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational",
        "evtx_files": ["TerminalServices.evtx", "TerminalServices-LocalSessionManager.evtx", "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational.evtx"],
        "category": "Remote Desktop Services / Session Tracking"
    },
    "rdp-remote-connection-manager": {
        "channel_str": "Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational",
        "evtx_files": ["TerminalServices-RemoteConnectionManager.evtx", "Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational.evtx"],
        "category": "Remote Desktop Services / Connection Tracking"
    },
    "security": {
        "channel_str": "Security",
        "evtx_files": ["Security.evtx"],
        "category": "Windows Security Auditing"
    },
    "system": {
        "channel_str": "System",
        "evtx_files": ["System.evtx"],
        "category": "System Service & Kernel Telemetry"
    },
    "application": {
        "channel_str": "Application",
        "evtx_files": ["Application.evtx"],
        "category": "Application & Software Crashes"
    },
    "sysmon": {
        "channel_str": "Microsoft-Windows-Sysmon/Operational",
        "evtx_files": ["Sysmon.evtx", "Microsoft-Windows-Sysmon/Operational.evtx"],
        "category": "Sysinternals Sysmon Sensor"
    },
    "powershell": {
        "channel_str": "Microsoft-Windows-PowerShell/Operational",
        "evtx_files": ["PowerShell.evtx", "Microsoft-Windows-PowerShell/Operational.evtx"],
        "category": "PowerShell Script Block Logging"
    },
    "windows-powershell": {
        "channel_str": "Windows PowerShell",
        "evtx_files": ["Windows PowerShell.evtx"],
        "category": "Classic PowerShell Engine"
    },
    "task-scheduler": {
        "channel_str": "Microsoft-Windows-TaskScheduler/Operational",
        "evtx_files": ["TaskScheduler.evtx", "Microsoft-Windows-TaskScheduler/Operational.evtx"],
        "category": "Task Scheduler Persistence"
    },
    "wmi-activity": {
        "channel_str": "Microsoft-Windows-WMI-Activity/Operational",
        "evtx_files": ["Microsoft-Windows-WMI-Activity/Operational.evtx", "WMI-Activity.evtx"],
        "category": "WMI Execution & Subscriptions"
    },
    "firewall": {
        "channel_str": "Microsoft-Windows-Windows Firewall With Advanced Security/Firewall",
        "evtx_files": ["Firewall.evtx"],
        "category": "Windows Firewall Rules & Drops"
    },
    "applocker": {
        "channel_str": "Microsoft-Windows-AppLocker/EXE and DLL",
        "evtx_files": ["AppLocker.evtx"],
        "category": "Application Whitelisting / AppLocker"
    },
    "ntlm": {
        "channel_str": "Microsoft-Windows-NTLM/Operational",
        "evtx_files": ["NTLM.evtx"],
        "category": "Legacy NTLM Authentication"
    },
    "dns-client": {
        "channel_str": "Microsoft-Windows-DNS-Client/Operational",
        "evtx_files": ["DNS-Client.evtx"],
        "category": "DNS Resolution & C2 Queries"
    }
}

# Precedence order when resolving colliding numeric EIDs (e.g. 21 in Sysmon vs RDP)
CHANNEL_PRECEDENCE = [
    "security",
    "defender",
    "rdp-local-session-manager",
    "sysmon",
    "powershell",
    "task-scheduler",
    "wmi-activity",
    "system",
    "application"
]

def load_existing_db(json_path: Path) -> Dict[str, Any]:
    if json_path.exists():
        try:
            with open(json_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception as e:
            print(f"Warning: Failed to parse existing {json_path}: {e}")
    return {}

def ensure_events_source(source_dir: str = None) -> Path:
    """Returns directory containing data/events from Cyber-Experts/evtx-parser."""
    if source_dir and os.path.isdir(source_dir):
        return Path(source_dir)

    # Check common fallback locations
    fallback = Path("/tmp/evtx-parser-tmp/data/events")
    if fallback.is_dir():
        return fallback

    # Clone sparse checkout into temporary directory
    temp_dir = tempfile.mkdtemp(prefix="evtx-parser-")
    print(f"Cloning Cyber-Experts/evtx-parser into {temp_dir}...")
    subprocess.check_call([
        "git", "clone", "--depth", "1", "--sparse",
        "https://github.com/Cyber-Experts/evtx-parser.git", temp_dir
    ])
    subprocess.check_call(["git", "sparse-checkout", "set", "data/events"], cwd=temp_dir)
    return Path(temp_dir) / "data" / "events"

def determine_severity(raw_event: Dict[str, Any], channel_slug: str) -> str:
    title_lower = (raw_event.get("title") or "").lower()
    summary_lower = (raw_event.get("summary") or "").lower()
    eid = str(raw_event.get("id", ""))

    if eid in ["5001", "1102", "104", "7045", "4697", "4720", "4726", "4728", "4732", "4738"]:
        return "CRITICAL TAMPERING" if eid in ["5001", "1102", "104"] else "SECURITY PRIVILEGED"

    if any(k in title_lower or k in summary_lower for k in ["disabled", "tamper", "cleared", "fail", "blocked", "malware"]):
        return "CRITICAL ALERT" if "malware" in title_lower else "HIGH ATTENTION"

    if any(k in title_lower or k in summary_lower for k in ["success", "logon", "created", "started", "enabled"]):
        return "AUDIT SUCCESS"

    return "AUDIT EVENT"

def format_key_fields(fields_raw: Any) -> List[str]:
    if not fields_raw:
        return []
    res = []
    if isinstance(fields_raw, list):
        for item in fields_raw:
            if isinstance(item, dict):
                name = item.get("name", "")
                desc = item.get("description", "")
                if name:
                    res.append(f"{name} ({desc})" if desc else name)
            elif isinstance(item, str):
                res.append(item)
    return res

def process_events(events_dir: Path, existing_db: Dict[str, Any]) -> Dict[str, Any]:
    print(f"Scanning YAML files in {events_dir}...")
    yaml_files = list(events_dir.glob("*/*.yaml"))
    print(f"Found {len(yaml_files)} YAML event definitions.")

    compiled = dict(existing_db)

    # Store multi-channel events grouped by numeric ID
    by_numeric_id: Dict[str, List[Dict[str, Any]]] = {}

    for y_file in yaml_files:
        channel_slug = y_file.parent.name
        with open(y_file, "r", encoding="utf-8") as f:
            try:
                raw = yaml.safe_load(f)
            except Exception as e:
                print(f"Error parsing {y_file}: {e}")
                continue

        if not raw or not isinstance(raw, dict):
            continue

        raw_id = raw.get("id")
        if raw_id is None:
            raw_id = y_file.stem
        eid_str = str(raw_id).strip()

        meta = CHANNEL_CANONICAL_NAMES.get(channel_slug, {
            "channel_str": raw.get("provider", channel_slug),
            "evtx_files": [f"{channel_slug}.evtx"],
            "category": raw.get("category", "Windows Audit Telemetry")
        })

        title = raw.get("title") or raw.get("shortTitle") or f"Event ID {eid_str}"
        summary = (raw.get("summary") or "").strip()
        description = (raw.get("description") or "").strip()

        investigation = raw.get("investigation") or []
        if isinstance(investigation, str):
            investigation = [investigation]

        attacker = raw.get("attacker") or []
        if isinstance(attacker, str):
            attacker = [attacker]

        benign = raw.get("benign") or []
        if isinstance(benign, str):
            benign = [benign]

        attack_list = raw.get("attack") or []
        if isinstance(attack_list, str):
            attack_list = [attack_list]

        key_fields = format_key_fields(raw.get("fields"))
        related = raw.get("related") or []
        if isinstance(related, str):
            related = [related]

        evtxparser_url = f"https://www.evtxparser.com/en/events/{channel_slug}/{eid_str}"

        # Severity assessment
        severity = determine_severity(raw, channel_slug)

        record = {
            "type": "eventid",
            "id": eid_str,
            "title": title,
            "channel": meta["channel_str"],
            "channel_slug": channel_slug,
            "category": meta["category"],
            "severity": severity,
            "summary": summary if summary else (description[:240] + "..." if len(description) > 240 else description),
            "description": description,
            "investigation_tips": investigation,
            "attacker_behavior": attacker,
            "benign_causes": benign,
            "mitre": attack_list,
            "key_fields": key_fields,
            "related": related,
            "url": evtxparser_url,
            "source": "Cyber-Experts evtx-parser / Microsoft Security"
        }

        # Index under channel-specific key: e.g. "defender/5001"
        compiled[f"{channel_slug}/{eid_str}"] = record

        # Group by numeric ID for canonical assignment
        by_numeric_id.setdefault(eid_str, []).append(record)

    # Resolve top-level numeric entries and secondary channel references
    for eid_str, records in by_numeric_id.items():
        if len(records) == 1:
            primary = dict(records[0])
            # Merge with existing curated if available
            if eid_str in compiled:
                existing_rec = compiled[eid_str]
                if isinstance(existing_rec, dict) and not existing_rec.get("unresolved"):
                    # Upgrade generic "Event ID XYZ" titles
                    if existing_rec.get("title", "").strip().lower() in [f"event id {eid_str}", f"eid {eid_str}"]:
                        existing_rec["title"] = primary["title"]
                    # Inject rich intelligence fields
                    for k in ["investigation_tips", "attacker_behavior", "benign_causes", "mitre", "key_fields", "description"]:
                        if primary.get(k) and not existing_rec.get(k):
                            existing_rec[k] = primary[k]
                    existing_rec["url"] = primary.get("url") or existing_rec.get("url")
                    compiled[f"Event ID {eid_str}"] = existing_rec
                    compiled[f"EID {eid_str}"] = existing_rec
                    continue
            compiled[eid_str] = primary
            compiled[f"Event ID {eid_str}"] = primary
            compiled[f"EID {eid_str}"] = primary
        else:
            # Sort by channel precedence
            def channel_score(r):
                slug = r.get("channel_slug", "")
                return CHANNEL_PRECEDENCE.index(slug) if slug in CHANNEL_PRECEDENCE else 999

            records.sort(key=channel_score)
            primary = dict(records[0])
            # Document alternative channels
            also_in = []
            for alt in records[1:]:
                also_in.append({
                    "channel": alt["channel"],
                    "channel_slug": alt.get("channel_slug"),
                    "title": alt["title"],
                    "url": alt["url"]
                })
            primary["also_in"] = also_in

            compiled[eid_str] = primary
            compiled[f"Event ID {eid_str}"] = primary
            compiled[f"EID {eid_str}"] = primary

    # Ensure all EVTX log channels are properly registered
    for slug, meta in CHANNEL_CANONICAL_NAMES.items():
        for evtx_name in meta["evtx_files"]:
            if evtx_name not in compiled:
                sample_eids = [r["id"] for r in by_numeric_id.values() for r in r if r.get("channel_slug") == slug][:6]
                key_events_str = [f"EID {e}" for e in sample_eids]
                compiled[evtx_name] = {
                    "type": "evtx",
                    "id": evtx_name,
                    "title": f"Windows {slug.replace('-', ' ').title()} Event Log",
                    "channel": meta["channel_str"],
                    "role": f"Forensic repository for {meta['category']}.",
                    "key_events": key_events_str,
                    "url": f"https://www.evtxparser.com/en/events/{slug}"
                }

    return compiled

def main():
    parser = argparse.ArgumentParser(description="Ingest Cyber-Experts evtx-parser into data/windows-events.json")
    parser.add_argument("--source-dir", help="Path to local data/events directory", default=None)
    parser.add_argument("--output", help="Path to output JSON file", default=str(TARGET_JSON))
    args = parser.parse_args()

    events_dir = ensure_events_source(args.source_dir)
    existing_db = load_existing_db(Path(args.output))
    print(f"Existing database had {len(existing_db)} keys.")

    compiled = process_events(events_dir, existing_db)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w", encoding="utf-8") as f:
        json.dump(compiled, f, indent=2, ensure_ascii=False)

    print(f"Successfully compiled {len(compiled)} records into {out_path}!")

if __name__ == "__main__":
    main()
