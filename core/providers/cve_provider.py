"""
core/providers/cve_provider.py
Data provider for CVE vulnerability records with tiered caching and Vulnerability Lookup API client.
"""

import json
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional
from core.providers.base import BaseProvider
from core.config import CVE_CACHE_PATH
from core.diagnostics import Diagnostics

class CveProvider(BaseProvider):
    name = "cve"

    def __init__(self, cache_file: Path = CVE_CACHE_PATH, allow_online: bool = True):
        super().__init__(cache_file=cache_file, allow_online=allow_online)

    def fetch(self, key: str) -> Optional[Dict[str, Any]]:
        cve_id = key.strip().upper()
        if not self.allow_online:
            return None

        url = f"https://vulnerability.circl.lu/api/cve/{cve_id}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Antigravity-Security-Tooling/1.0 (Vulnerability Lookup Client)",
                "Accept": "application/json"
            }
        )

        try:
            Diagnostics.debug_log(f"[CveProvider] Querying Vulnerability Lookup API for {cve_id}...")
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if not data or not isinstance(data, dict) or ("id" not in data and "summary" not in data):
                Diagnostics.debug_log(f"[CveProvider] CVE {cve_id} not found in CIRCL Vulnerability Lookup.")
                return None

            summary = data.get("summary", "No detailed synopsis available.")
            cvss_score = data.get("cvss")
            severity = "CRITICAL" if cvss_score and float(cvss_score) >= 9.0 else "HIGH" if cvss_score and float(cvss_score) >= 7.0 else "MEDIUM"

            affected = []
            vulnerable_configs = data.get("vulnerable_configuration", [])
            for cpe in vulnerable_configs[:4]:
                parts = cpe.split(":")
                if len(parts) > 4:
                    affected.append(f"{parts[3].capitalize()} {parts[4]}")

            return {
                "type": "cve",
                "id": cve_id,
                "title": f"{cve_id}: Security Vulnerability",
                "summary": summary[:320] + ("..." if len(summary) > 320 else ""),
                "score": cvss_score,
                "severity": severity,
                "affected": affected,
                "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}"
            }
        except Exception as err:
            Diagnostics.debug_log(f"[CveProvider] Online fetch failed for {cve_id}: {err}")
            return None
