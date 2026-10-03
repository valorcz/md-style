#!/usr/bin/env python3
"""
scripts/enrich-identifiers.py
Offline-first knowledge enrichment for cybersecurity identifiers:
- MITRE ATT&CK Enterprise techniques (Txxxx, Txxxx.yyy) via data/mitre-enterprise.json
- CVE identifiers (CVE-YYYY-NNNN+) via CIRCL Vulnerability Lookup with local cache
- GitHub Security Advisories (GHSA-...) via GitHub Advisory API with local cache
"""

import sys
import os
import re
import json
import urllib.request
import urllib.error

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, ".."))
MITRE_DB_PATH = os.path.join(PROJECT_DIR, "data", "mitre-enterprise.json")
CACHE_DIR = os.path.expanduser("~/.cache/md-style")
VULN_CACHE_FILE = os.path.join(CACHE_DIR, "vulns.json")

os.makedirs(CACHE_DIR, exist_ok=True)

# Load MITRE DB
mitre_db = {}
if os.path.exists(MITRE_DB_PATH):
    try:
        with open(MITRE_DB_PATH, "r", encoding="utf-8") as f:
            mitre_db = json.load(f)
    except Exception as e:
        sys.stderr.write(f"[WARN] Failed to load MITRE DB: {e}\n")

# Load Windows Events DB
WIN_EVENTS_PATH = os.path.join(PROJECT_DIR, "data", "windows-events.json")
win_events_db = {}
if os.path.exists(WIN_EVENTS_PATH):
    try:
        with open(WIN_EVENTS_PATH, "r", encoding="utf-8") as f:
            win_events_db = json.load(f)
    except Exception as e:
        sys.stderr.write(f"[WARN] Failed to load Windows events DB: {e}\n")

# Load Vuln Cache
vuln_cache = {}
if os.path.exists(VULN_CACHE_FILE):
    try:
        with open(VULN_CACHE_FILE, "r", encoding="utf-8") as f:
            vuln_cache = json.load(f)
    except Exception as e:
        sys.stderr.write(f"[WARN] Failed to load vuln cache: {e}\n")

def save_vuln_cache():
    try:
        with open(VULN_CACHE_FILE, "w", encoding="utf-8") as f:
            json.dump(vuln_cache, f, indent=2, ensure_ascii=False)
    except Exception as e:
        sys.stderr.write(f"[WARN] Failed to save vuln cache: {e}\n")

def fetch_cve(cve_id):
    cve_id = cve_id.upper().strip()
    if cve_id in vuln_cache:
        return vuln_cache[cve_id]

    url = f"https://vulnerability.circl.lu/api/vulnerability/{cve_id}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "md-style-enricher/1.0", "Accept": "application/json"}
    )
    data = None
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except Exception as e:
        # Graceful fallback on network timeout/offline
        record = {
            "type": "cve",
            "id": cve_id,
            "title": f"Security Vulnerability {cve_id}",
            "summary": "External lookup unavailable (offline build or unlisted CVE).",
            "severity": "UNKNOWN",
            "score": None,
            "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}",
            "offline": True
        }
        vuln_cache[cve_id] = record
        return record

    if not data:
        return None

    # Parse CVE 5.0 schema from CIRCL
    cna = data.get("containers", {}).get("cna", {})
    title = cna.get("title") or f"Vulnerability {cve_id}"
    descriptions = cna.get("descriptions", [])
    desc_text = descriptions[0].get("value", "") if descriptions else ""
    if len(desc_text) > 400:
        desc_text = desc_text[:397] + "..."

    # Extract CVSS
    score = None
    severity = "HIGH"
    for metric in cna.get("metrics", []):
        for k, v in metric.items():
            if isinstance(v, dict) and "baseScore" in v:
                score = v.get("baseScore")
                severity = (v.get("baseSeverity") or "HIGH").upper()
                break
        if score is not None:
            break

    # Extract affected products
    affected_list = []
    for aff in cna.get("affected", []):
        prod = aff.get("product") or aff.get("packageName")
        if prod and prod not in affected_list:
            affected_list.append(prod)

    record = {
        "type": "cve",
        "id": cve_id,
        "title": title,
        "summary": desc_text or "No detailed description provided.",
        "severity": severity,
        "score": score,
        "affected": affected_list[:5],
        "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}"
    }
    vuln_cache[cve_id] = record
    return record

def fetch_ghsa(ghsa_id):
    ghsa_id = ghsa_id.strip()
    if ghsa_id in vuln_cache:
        return vuln_cache[ghsa_id]

    url = f"https://api.github.com/advisories/{ghsa_id}"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "md-style-enricher/1.0", "Accept": "application/vnd.github+json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=3) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            record = {
                "type": "ghsa",
                "id": ghsa_id,
                "title": data.get("summary") or f"GitHub Advisory {ghsa_id}",
                "summary": (data.get("description") or "")[:350],
                "severity": (data.get("severity") or "HIGH").upper(),
                "score": data.get("cvss", {}).get("score"),
                "cve": data.get("cve_id"),
                "url": f"https://github.com/advisories/{ghsa_id}"
            }
            vuln_cache[ghsa_id] = record
            return record
    except Exception as e:
        record = {
            "type": "ghsa",
            "id": ghsa_id,
            "title": f"GitHub Advisory {ghsa_id}",
            "summary": "External lookup unavailable (offline or rate-limited).",
            "severity": "HIGH",
            "score": None,
            "url": f"https://github.com/advisories/{ghsa_id}",
            "offline": True
        }
        vuln_cache[ghsa_id] = record
        return record

def enrich_identifier(ident):
    ident = ident.strip()
    # 1. MITRE ATT&CK: Txxxx or Txxxx.yyy or TAxxxx
    mitre_match = re.match(r"^(T\d{4}(?:\.\d{3})?)$", ident, re.IGNORECASE)
    if mitre_match:
        mid = mitre_match.group(1).upper()
        if mid in mitre_db:
            m = mitre_db[mid]
            return {
                "type": "mitre",
                "id": mid,
                "name": m.get("name"),
                "tactics": m.get("tactics", []),
                "platforms": m.get("platforms", []),
                "summary": m.get("summary", ""),
                "url": m.get("url") or f"https://attack.mitre.org/techniques/{mid}/"
            }
        else:
            return {
                "type": "mitre",
                "id": mid,
                "name": f"MITRE ATT&CK Technique {mid}",
                "tactics": ["Adversary Technique"],
                "summary": "Standard Enterprise ATT&CK matrix technique.",
                "url": f"https://attack.mitre.org/techniques/{mid}/"
            }

    # 2. CVE: CVE-YYYY-NNNN+
    if re.match(r"^CVE-\d{4}-\d{4,}$", ident, re.IGNORECASE):
        return fetch_cve(ident)

    # 3. GHSA
    if re.match(r"^GHSA-[A-Za-z0-9]+-[A-Za-z0-9]+-[A-Za-z0-9]+$", ident, re.IGNORECASE):
        return fetch_ghsa(ident)

    # 4. Windows Event Log File: e.g. Security.evtx, System.evtx, Sysmon.evtx
    if ident.lower().endswith(".evtx"):
        base_evtx = os.path.basename(ident)
        if ident in win_events_db:
            return win_events_db[ident]
        elif base_evtx in win_events_db:
            return win_events_db[base_evtx]
        else:
            return {
                "type": "evtx",
                "id": ident,
                "title": f"Windows Event Log ({base_evtx})",
                "channel": base_evtx.replace(".evtx", ""),
                "role": "Binary XML Windows Event Log archive.",
                "url": "https://learn.microsoft.com/en-us/windows/win32/eventlog/event-logging"
            }

    # 5. Windows Event ID: e.g. "Event ID 4624", "Event 4624", "EID 4624", "4624"
    ev_match = re.match(r"^(?:event\s*(?:id)?:?|eid:?)\s*(\d+)$", ident, re.IGNORECASE)
    eid_val = ev_match.group(1) if ev_match else (ident if ident in win_events_db and win_events_db[ident].get("type") == "eventid" else None)
    if eid_val and eid_val in win_events_db:
        return win_events_db[eid_val]

    return None

def main():
    if len(sys.argv) > 1:
        identifiers = sys.argv[1:]
    else:
        try:
            raw = sys.stdin.read().strip()
            if not raw:
                print("{}")
                return
            identifiers = json.loads(raw) if raw.startswith("[") else raw.split()
        except Exception:
            identifiers = []

    results = {}
    cache_dirty = False
    for ident in identifiers:
        res = enrich_identifier(ident)
        if res:
            results[ident] = res
            cache_dirty = True

    if cache_dirty:
        save_vuln_cache()

    print(json.dumps(results, ensure_ascii=False))

if __name__ == "__main__":
    main()
