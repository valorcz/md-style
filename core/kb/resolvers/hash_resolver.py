"""
core/kb/resolvers/hash_resolver.py
Dedicated resolver for cryptographic hashes (MD5, SHA-1, SHA-256).
Provides cryptographic integrity analysis, collision status, algorithm metadata,
well-known null/empty hash identification, and online threat intelligence
via VirusTotal API v3 (when API key is provided).
"""

import re
import json
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance
from core.config import HASH_CACHE_PATH, get_threat_intel_api_key
from core.diagnostics import Diagnostics
from core.i18n import I18nCatalog

# Hash pattern regexes
MD5_REGEX = re.compile(r"\b[a-fA-F0-9]{32}\b")
SHA1_REGEX = re.compile(r"\b[a-fA-F0-9]{40}\b")
SHA256_REGEX = re.compile(r"\b[a-fA-F0-9]{64}\b")

# Well-known hashes
WELL_KNOWN_HASHES = {
    "d41d8cd98f00b204e9800998ecf8427e": {
        "name": "Empty File (Zero-Byte)",
        "type": "MD5",
        "description": "Standard MD5 hash of an empty string or 0-byte file (NULL byte sequence)."
    },
    "da39a3ee5e6b4b0d3255bfef95601890afd80709": {
        "name": "Empty File (Zero-Byte)",
        "type": "SHA-1",
        "description": "Standard SHA-1 hash of an empty string or 0-byte file."
    },
    "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855": {
        "name": "Empty File (Zero-Byte)",
        "type": "SHA-256",
        "description": "Standard NIST SHA-256 hash of an empty string or 0-byte file."
    }
}


class HashResolver(BaseResolver):
    name = "hash"

    def __init__(
        self,
        cache_file: Path = HASH_CACHE_PATH,
        catalog: Optional[I18nCatalog] = None
    ):
        self.cache_file = cache_file
        self.catalog = catalog or I18nCatalog("en")
        self.cache: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def _save_cache(self) -> None:
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def can_handle(self, token: str) -> bool:
        t = token.strip()
        length = len(t)
        if length not in (32, 40, 64):
            return False
        return bool(re.fullmatch(r"^[a-fA-F0-9]+$", t))

    def extract_candidates(self, text: str) -> List[str]:
        candidates: List[str] = []
        # Match SHA-256 (64 hex chars)
        for m in SHA256_REGEX.finditer(text):
            candidates.append(m.group(0))

        # Match SHA-1 (40 hex chars)
        for m in SHA1_REGEX.finditer(text):
            candidates.append(m.group(0))

        # Match MD5 (32 hex chars)
        for m in MD5_REGEX.finditer(text):
            candidates.append(m.group(0))

        return list(set(candidates))

    def _get_algorithm_meta(self, hash_str: str) -> Dict[str, Any]:
        length = len(hash_str)
        if length == 32:
            return {
                "algorithm": "MD5",
                "bit_length": 128,
                "security_status": "Cryptographically Broken (Vulnerable to Pre-image & Collision Attacks)",
                "recommended_use": "Legacy Checksum Verification Only"
            }
        elif length == 40:
            return {
                "algorithm": "SHA-1",
                "bit_length": 160,
                "security_status": "Cryptographically Deprecated (Practical Collision Attacks Demonstrated)",
                "recommended_use": "Git commit hashing / legacy compatibility"
            }
        elif length == 64:
            return {
                "algorithm": "SHA-256",
                "bit_length": 256,
                "security_status": "Cryptographically Secure (NIST FIPS 180-4 Approved)",
                "recommended_use": "Digital Signatures, File Integrity, Forensic Evidence Verification"
            }
        else:
            return {
                "algorithm": "Unknown",
                "bit_length": length * 4,
                "security_status": "Unknown",
                "recommended_use": "Unspecified"
            }

    def _query_virustotal(self, hash_str: str, api_key: str) -> Optional[Dict[str, Any]]:
        """Queries VirusTotal API v3 /files/{id} endpoint."""
        url = f"https://www.virustotal.com/api/v3/files/{urllib.parse.quote(hash_str)}"
        req = urllib.request.Request(
            url,
            headers={
                "x-apikey": api_key,
                "User-Agent": "Antigravity-Security-Tooling/2.0 (HashResolver)",
                "Accept": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=5.0) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data.get("data", {}).get("attributes")
        except Exception as e:
            Diagnostics.debug_log(f"VirusTotal API query failed for {hash_str}: {e}")
            return None

    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        clean_hash = token.strip().lower()
        if not self.can_handle(clean_hash):
            return None

        algo_meta = self._get_algorithm_meta(clean_hash)
        algo_name = algo_meta["algorithm"]

        # Check Cache
        cached_data = self.cache.get(clean_hash) if not force_refresh else None
        vt_data = cached_data.get("virustotal") if cached_data else None

        # Online VT lookup if API key present
        vt_key = get_threat_intel_api_key("virustotal")
        if allow_online and not vt_data and vt_key:
            vt_res = self._query_virustotal(clean_hash, vt_key)
            if vt_res:
                vt_data = vt_res
                self.cache[clean_hash] = {
                    "virustotal": vt_data,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                self._save_cache()

        # Check well-known hashes
        well_known = WELL_KNOWN_HASHES.get(clean_hash)

        # Derive properties
        malicious_count = 0
        total_engines = 0
        file_type = "Cryptographic Digest"
        threat_label = ""
        meaningful_name = clean_hash[:12] + "..." + clean_hash[-6:]

        if well_known:
            title = f"{algo_name}: {well_known['name']}"
            summary = well_known["description"]
            severity = "INFO"
            badge = f"{algo_name} NULL HASH"
        elif vt_data:
            stats = vt_data.get("last_analysis_stats", {})
            malicious_count = stats.get("malicious", 0)
            suspicious_count = stats.get("suspicious", 0)
            total_engines = sum(stats.values()) if stats else 72
            file_type = vt_data.get("type_description", "Binary Executable")
            threat_label = vt_data.get("popular_threat_classification", {}).get("suggested_threat_label", "")
            names = vt_data.get("names", [])
            if names:
                meaningful_name = names[0]

            if malicious_count >= 10:
                severity = "CRITICAL"
                badge = f"VT {malicious_count}/{total_engines} MALICIOUS"
            elif malicious_count > 0:
                severity = "HIGH"
                badge = f"VT {malicious_count}/{total_engines} SUSPICIOUS"
            else:
                severity = "INFO"
                badge = f"VT {total_engines} CLEAN"

            title = f"{algo_name}: {meaningful_name}"
            summary = (
                f"VirusTotal forensic analysis for {meaningful_name}. "
                f"Flagged as malicious by {malicious_count} of {total_engines} security engines. "
                + (f"Threat Classification: {threat_label}. " if threat_label else "")
                + f"Identified as {file_type}."
            )
        else:
            title = f"{algo_name} Digest: {meaningful_name}"
            severity = "INFO"
            badge = f"{algo_name} HASH"
            summary = (
                f"{algo_meta['bit_length']}-bit {algo_name} cryptographic file hash. "
                f"Status: {algo_meta['security_status']}."
            )

        details = {
            "Hash Value": clean_hash,
            "Algorithm": algo_name,
            "Bit Length": f"{algo_meta['bit_length']} bits",
            "Security Status": algo_meta["security_status"],
            "Recommended Use": algo_meta["recommended_use"],
            "Detection Ratio": f"{malicious_count} / {total_engines} engines" if total_engines else "Unchecked",
            "File Type Classification": file_type,
            "Identified Threat Label": threat_label or "None assigned"
        }

        references = [
            {"title": "VirusTotal Intelligence", "url": f"https://www.virustotal.com/gui/file/{clean_hash}"},
            {"title": "MalwareBazaar Sample Search", "url": f"https://bazaar.abuse.ch/sample/{clean_hash}/"},
            {"title": "Hybrid Analysis Sandbox", "url": f"https://www.hybrid-analysis.com/search?query={clean_hash}"}
        ]

        relationships: List[Dict[str, str]] = []
        if threat_label and "mimikatz" in threat_label.lower():
            relationships.append({"target": "T1003.001", "type": "mitre", "relation": "associated_technique"})

        prov = Provenance(
            source="api:virustotal" if vt_data else "catalog:cryptographic",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="resolved"
        )

        return Entity(
            id=clean_hash,
            domain="cyber",
            type="hash",
            label=clean_hash,
            title=title,
            severity=severity,
            badge=badge,
            summary=summary,
            attributes={
                "Algorithm": algo_name,
                "Length": f"{algo_meta['bit_length']} bits",
                "Detection": f"{malicious_count}/{total_engines}" if total_engines else "N/A",
                "Type": file_type
            },
            metrics={
                "bit_length": algo_meta["bit_length"],
                "malicious_engines": malicious_count,
                "total_engines": total_engines
            },
            classification={
                "algorithm": algo_name,
                "file_type": file_type,
                "threat_label": threat_label
            },
            details=details,
            relationships=relationships,
            references=references,
            provenance=prov,
            aliases=[clean_hash, clean_hash.upper(), meaningful_name]
        )
