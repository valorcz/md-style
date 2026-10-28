"""
core/kb/sync.py
Unified Synchronization Engine for Finite Knowledge Pack Catalogs:
  1. MITRE ATT&CK Enterprise Matrix (via official MITRE CTI STIX repository)
  2. Windows Event IDs & EVTX Channels (via Zimmerman Maps, Hayabusa, and UWS specs)
"""

import os
import re
import sys
import json
import time
import zipfile
import io
import xml.etree.ElementTree as ET
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple

from core.config import (
    DATA_DIR,
    MITRE_DB_PATH,
    WIN_EVENTS_DB_PATH,
    WIN_EVENTS_CACHE_PATH,
    CVE_DB_PATH,
    CWE_DB_PATH,
    CWE_CACHE_PATH,
    DEFAULT_MITRE_CWE_URL,
    INTEL_CACHE_DIR,
)
from core.diagnostics import Diagnostics, Colors

DEFAULT_MITRE_STIX_URL = "https://raw.githubusercontent.com/mitre/cti/master/enterprise-attack/enterprise-attack.json"

def _load_evtx_catalogs() -> Tuple[Dict[str, Dict[str, Any]], Dict[str, str]]:
    """Loads authoritative EVTX forensic channel catalog and shorthand map from JSON SSOT."""
    evtx_json_path = DATA_DIR / "catalogs" / "evtx_channels.json"
    if evtx_json_path.is_file():
        try:
            raw = json.loads(evtx_json_path.read_text(encoding="utf-8"))
            return raw.get("channels", {}), raw.get("shorthands", {})
        except Exception as e:
            Diagnostics.warn(f"Failed to load EVTX catalog from {evtx_json_path}: {e}")
    return {}, {}


EXPANDED_EVTX_CHANNELS, EVTX_SHORTHAND_MAP = _load_evtx_catalogs()


def clean_mitre_text(raw_text: str, max_chars: int = 340) -> str:
    if not raw_text:
        return "MITRE ATT&CK enterprise adversary technique."
    # Strip markdown citations e.g. (Citation: ...)
    cleaned = re.sub(r'\(Citation:[^\)]+\)', '', raw_text)
    # Strip markdown hyperlinks e.g. [text](url) -> text
    cleaned = re.sub(r'\[([^\]]+)\]\([^\)]+\)', r'\1', cleaned)
    # Strip markdown formatting headers or code fences
    cleaned = re.sub(r'[`#*]', '', cleaned)
    # Normalize whitespaces
    cleaned = ' '.join(cleaned.split())
    if len(cleaned) > max_chars:
        return cleaned[:max_chars].rstrip() + "..."
    return cleaned


def sync_mitre_attack(
    source_url: str = DEFAULT_MITRE_STIX_URL,
    output_path: Path = MITRE_DB_PATH,
    verbose: bool = False
) -> int:
    """
    Downloads official MITRE CTI STIX repository and compiles clean lightweight JSON.
    """
    if verbose:
        Diagnostics.info(f"Syncing MITRE ATT&CK database from {source_url}...")

    req = urllib.request.Request(
        source_url,
        headers={"User-Agent": "md-style-Knowledge-Sync/1.0 (Enterprise ATT&CK Compiler)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw_bytes = resp.read()
    except Exception as err:
        Diagnostics.warn(f"Failed to fetch MITRE CTI STIX repository: {err}")
        if output_path.exists():
            return len(json.loads(output_path.read_text(encoding="utf-8")))
        return 0

    try:
        stix_data = json.loads(raw_bytes.decode("utf-8"))
    except Exception as err:
        Diagnostics.warn(f"Failed to parse MITRE STIX JSON payload: {err}")
        return 0

    objects = stix_data.get("objects", [])
    techniques_db: Dict[str, Any] = {}

    for obj in objects:
        if obj.get("type") != "attack-pattern":
            continue
        if obj.get("revoked", False) or obj.get("x_mitre_deprecated", False):
            continue

        external_refs = obj.get("external_references", [])
        technique_id = None
        mitre_url = None

        for ref in external_refs:
            if ref.get("source_name") == "mitre-attack":
                technique_id = ref.get("external_id")
                mitre_url = ref.get("url")
                break

        if not technique_id:
            continue

        tactics = []
        for kill_chain in obj.get("kill_chain_phases", []):
            if kill_chain.get("kill_chain_name") == "mitre-attack":
                phase = kill_chain.get("phase_name", "").replace("-", " ").title()
                if phase:
                    tactics.append(phase)

        tactic_str = " / ".join(tactics) if tactics else "Enterprise Tactic"
        name = obj.get("name", "Unknown Technique").strip()
        description = clean_mitre_text(obj.get("description", ""))

        platforms = obj.get("x_mitre_platforms", [])
        is_subtechnique = obj.get("x_mitre_is_subtechnique", False)

        techniques_db[technique_id] = {
            "type": "mitre",
            "id": technique_id,
            "title": name,
            "tactic": tactic_str,
            "summary": description,
            "platforms": platforms,
            "is_subtechnique": is_subtechnique,
            "url": mitre_url or f"https://attack.mitre.org/techniques/{technique_id.replace('.', '/')}/"
        }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(techniques_db, f, indent=2, ensure_ascii=False)

    # Mirror to user intel cache
    try:
        INTEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        mirror_path = INTEL_CACHE_DIR / "mitre-attack.json"
        mirror_path.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass

    if verbose:
        Diagnostics.success(f"MITRE database synced: {len(techniques_db)} techniques -> {output_path}")

    return len(techniques_db)


def sync_windows_events_and_evtx(
    output_path: Path = WIN_EVENTS_DB_PATH,
    verbose: bool = False
) -> int:
    """
    Merges authoritative Windows Event IDs and Expanded EVTX channel definitions
    into a single unified data/windows-events.json database.
    """
    if verbose:
        Diagnostics.info(f"Syncing Windows Events & EVTX catalog to {output_path}...")

    existing_db: Dict[str, Any] = {}
    if output_path.exists():
        try:
            existing_db = json.loads(output_path.read_text(encoding="utf-8"))
        except Exception:
            existing_db = {}

    # 1. Inject or update all expanded EVTX channel definitions
    for channel_key, channel_info in EXPANDED_EVTX_CHANNELS.items():
        existing_db[channel_key] = channel_info
        # Also store bare channel name if different (e.g. "Security" for "Security.evtx")
        bare_name = channel_info.get("channel")
        if bare_name and bare_name not in existing_db:
            existing_db[bare_name] = channel_info

    # 2. Inject shorthand aliases
    for alias, canonical in EVTX_SHORTHAND_MAP.items():
        if canonical in existing_db:
            existing_db[alias] = existing_db[canonical]

    # 3. Write unified database
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(existing_db, f, indent=2, ensure_ascii=False)

    # Mirror to user cache
    try:
        INTEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        WIN_EVENTS_CACHE_PATH.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass

    if verbose:
        Diagnostics.success(f"Windows Events & EVTX catalog synced: {len(existing_db)} entries -> {output_path}")

    return len(existing_db)


# --------------------------------------------------------------------------
# Authoritative 2024 / 2023 CWE Top 25 Most Dangerous Weaknesses Ranking
# (Canonical list from MITRE View-1425)
# --------------------------------------------------------------------------
CWE_TOP_25_RANKS: Dict[str, int] = {
    "787": 1,   # Out-of-bounds Write
    "79": 2,    # Cross-site Scripting
    "89": 3,    # SQL Injection
    "416": 4,   # Use After Free
    "78": 5,    # OS Command Injection
    "20": 6,    # Improper Input Validation
    "125": 7,   # Out-of-bounds Read
    "22": 8,    # Path Traversal
    "352": 9,   # Cross-Site Request Forgery (CSRF)
    "434": 10,  # Unrestricted Upload of File with Dangerous Type
    "862": 11,  # Missing Authorization
    "476": 12,  # NULL Pointer Dereference
    "287": 13,  # Improper Authentication
    "190": 14,  # Integer Overflow
    "502": 15,  # Deserialization of Untrusted Data
    "77": 16,   # Command Injection
    "119": 17,  # Buffer Errors
    "798": 18,  # Hard-coded Credentials
    "918": 19,  # Server-Side Request Forgery (SSRF)
    "306": 20,  # Missing Authentication for Critical Function
    "362": 21,  # Race Condition / Concurrent Execution
    "269": 22,  # Improper Privilege Management
    "94": 23,   # Code Injection
    "863": 24,  # Incorrect Authorization
    "276": 25,  # Incorrect Default Permissions
}

# Curated CAPEC -> MITRE ATT&CK Technique mappings
CAPEC_TO_ATTACK: Dict[str, List[str]] = {
    "100": ["T1190", "T1068", "T1203"], # Overflow Buffers
    "586": ["T1190", "T1059"],          # Object Injection / Deserialization
    "66": ["T1190"],                    # SQL Injection
    "88": ["T1059"],                    # OS Command Injection
    "63": ["T1189"],                    # Cross-Site Scripting
    "115": ["T1078", "T1556"],          # Authentication Bypass
    "37": ["T1552.001"],                # Retrieve Embedded Sensitive Data
    "126": ["T1083", "T1005"],          # Path Traversal
    "153": ["T1059.001"],               # Command Execution
    "163": ["T1203", "T1566.001"],      # Client Exploit
    "242": ["T1055"],                   # Code Injection
    "664": ["T1190"],                   # Server Side Request Forgery
}

# Heuristic CWE -> MITRE ATT&CK technique linkages
CWE_TO_ATTACK_HEURISTICS: Dict[str, List[str]] = {
    "CWE-787": ["T1190", "T1068", "T1203"],
    "CWE-120": ["T1190", "T1068", "T1203"],
    "CWE-125": ["T1005", "T1203"],
    "CWE-416": ["T1068", "T1203"],
    "CWE-119": ["T1190", "T1068", "T1203"],
    "CWE-502": ["T1190", "T1059"],
    "CWE-89":  ["T1190"],
    "CWE-78":  ["T1059", "T1190"],
    "CWE-77":  ["T1059", "T1190"],
    "CWE-94":  ["T1059", "T1190"],
    "CWE-22":  ["T1083", "T1005"],
    "CWE-434": ["T1190", "T1505.003"],
    "CWE-798": ["T1552.001", "T1078"],
    "CWE-287": ["T1078"],
    "CWE-289": ["T1078", "T1556"],
    "CWE-306": ["T1078"],
    "CWE-862": ["T1078", "T1068"],
    "CWE-863": ["T1078", "T1068"],
    "CWE-269": ["T1068", "T1078"],
    "CWE-276": ["T1078"],
    "CWE-918": ["T1190"],
    "CWE-400": ["T1498", "T1499"],
    "CWE-770": ["T1499"],
    "CWE-20":  ["T1190", "T1059"],
    "CWE-200": ["T1005", "T1083"],
    "CWE-917": ["T1190", "T1059"],
}


def _parse_cwe_xml(xml_file) -> Dict[str, Any]:
    """Parses streaming MITRE CWE XML payload into structured records."""
    cwe_db: Dict[str, Any] = {}

    for event, elem in ET.iterparse(xml_file, events=("end",)):
        if elem.tag.endswith("Weakness"):
            wid = elem.attrib.get("ID", "").strip()
            if not wid:
                elem.clear()
                continue

            name = elem.attrib.get("Name", "").strip()
            abstraction = elem.attrib.get("Abstraction", "Base")
            status = elem.attrib.get("Status", "Draft")
            cwe_key = f"CWE-{wid}"

            desc_el = elem.find("{*}Description")
            desc = desc_el.text.strip() if desc_el is not None and desc_el.text else ""
            ext_el = elem.find("{*}Extended_Description")
            ext_desc = ext_el.text.strip() if ext_el is not None and ext_el.text else ""

            # Common Consequences (Scope & Technical Impact)
            scopes: set = set()
            impacts: set = set()
            for cons in elem.findall(".//{*}Consequence"):
                for sc in cons.findall("{*}Scope"):
                    if sc.text:
                        scopes.add(sc.text.strip())
                for imp in cons.findall("{*}Impact"):
                    if imp.text:
                        impacts.add(imp.text.strip())

            # Potential Mitigations
            mitigations: List[str] = []
            for mit in elem.findall(".//{*}Mitigation"):
                phase_el = mit.find("{*}Phase")
                desc_m_el = mit.find("{*}Description")
                strat_el = mit.find("{*}Strategy")
                p = phase_el.text.strip() if phase_el is not None and phase_el.text else ""
                d = desc_m_el.text.strip() if desc_m_el is not None and desc_m_el.text else ""
                s = strat_el.text.strip() if strat_el is not None and strat_el.text else ""
                if d:
                    entry = f"[{p}] {d}" if p else d
                    if s:
                        entry = f"{s}: {entry}"
                    mitigations.append(entry)

            # Detection Methods
            detection_methods: List[str] = []
            for det in elem.findall(".//{*}Detection_Method"):
                method_el = det.find("{*}Method")
                desc_d_el = det.find("{*}Description")
                m_name = method_el.text.strip() if method_el is not None and method_el.text else ""
                m_desc = desc_d_el.text.strip() if desc_d_el is not None and desc_d_el.text else ""
                if m_name:
                    detection_methods.append(f"{m_name}: {m_desc}" if m_desc else m_name)

            # Applicable Platforms
            platforms: List[str] = []
            for lang in elem.findall(".//{*}Language"):
                l_name = lang.attrib.get("Name")
                if l_name and l_name not in platforms and "Not Language" not in l_name:
                    platforms.append(l_name)

            # Related Attack Patterns (CAPEC)
            capecs: List[str] = []
            for rap in elem.findall(".//{*}Related_Attack_Pattern"):
                cid = rap.attrib.get("CAPEC_ID")
                if cid and cid not in capecs:
                    capecs.append(cid)

            # Correlate with MITRE ATT&CK techniques
            mitre_techniques: List[str] = []
            for cid in capecs:
                for tid in CAPEC_TO_ATTACK.get(cid, []):
                    if tid not in mitre_techniques:
                        mitre_techniques.append(tid)

            # Add heuristic techniques if not already present
            for tid in CWE_TO_ATTACK_HEURISTICS.get(cwe_key, []):
                if tid not in mitre_techniques:
                    mitre_techniques.append(tid)

            # Related Weaknesses (Parent/Child)
            parents: List[str] = []
            for rw in elem.findall(".//{*}Related_Weakness"):
                nature = rw.attrib.get("Nature")
                rw_id = rw.attrib.get("CWE_ID")
                if nature == "ChildOf" and rw_id:
                    parents.append(f"CWE-{rw_id}")

            top25_rank = CWE_TOP_25_RANKS.get(wid)

            cwe_db[cwe_key] = {
                "id": cwe_key,
                "title": name,
                "abstraction": abstraction,
                "status": status,
                "summary": desc,
                "extended_description": ext_desc,
                "scopes": sorted(list(scopes)),
                "impacts": sorted(list(impacts)),
                "mitigations": mitigations[:4],
                "detection_methods": detection_methods[:3],
                "platforms": platforms[:6],
                "capecs": capecs,
                "mitre_techniques": mitre_techniques,
                "parent_cwes": parents,
                "top25_rank": top25_rank,
                "url": f"https://cwe.mitre.org/data/definitions/{wid}.html"
            }
            elem.clear()

    return cwe_db


def sync_cwe_catalog(
    source_url: str = DEFAULT_MITRE_CWE_URL,
    output_path: Path = CWE_DB_PATH,
    verbose: bool = False
) -> int:
    """
    Downloads official canonical MITRE CWE XML release, parses weakness records,
    correlates with MITRE ATT&CK techniques, and compiles data/cwe.json.
    """
    if verbose:
        Diagnostics.info(f"Syncing MITRE CWE catalog from {source_url}...")

    req = urllib.request.Request(
        source_url,
        headers={"User-Agent": "md-style-Knowledge-Sync/1.0 (CWE Compiler)"}
    )

    try:
        with urllib.request.urlopen(req, timeout=45) as resp:
            raw_bytes = resp.read()
    except Exception as err:
        Diagnostics.warn(f"Failed to fetch MITRE CWE archive: {err}")
        if output_path.exists():
            try:
                return len(json.loads(output_path.read_text(encoding="utf-8")))
            except Exception:
                pass
        return 0

    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as z:
            xml_names = [n for n in z.namelist() if n.endswith(".xml")]
            if not xml_names:
                Diagnostics.warn("No XML found in MITRE CWE zip archive.")
                return 0
            with z.open(xml_names[0]) as xml_file:
                cwe_db = _parse_cwe_xml(xml_file)
    except Exception as err:
        Diagnostics.warn(f"Failed to parse MITRE CWE XML payload: {err}")
        return 0

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(cwe_db, f, indent=2, ensure_ascii=False)

    try:
        INTEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
        mirror_path = INTEL_CACHE_DIR / "cwe.json"
        mirror_path.write_text(output_path.read_text(encoding="utf-8"), encoding="utf-8")
    except Exception:
        pass

    if verbose:
        Diagnostics.success(f"CWE catalog synced: {len(cwe_db)} weaknesses -> {output_path}")

    return len(cwe_db)


def sync_all_catalogs(verbose: bool = True) -> Dict[str, int]:
    """Runs all knowledge base synchronizations."""
    mitre_count = sync_mitre_attack(verbose=verbose)
    winevt_count = sync_windows_events_and_evtx(verbose=verbose)
    cwe_count = sync_cwe_catalog(verbose=verbose)
    return {
        "mitre_techniques": mitre_count,
        "windows_events_and_channels": winevt_count,
        "cwe_weaknesses": cwe_count,
    }


if __name__ == "__main__":
    results = sync_all_catalogs(verbose=True)
    print("\n[SYNC COMPLETE]", results)

