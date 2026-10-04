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

            if not data or not isinstance(data, dict):
                Diagnostics.debug_log(f"[CveProvider] CVE {cve_id} invalid response from CIRCL.")
                return None

            cna = data.get("containers", {}).get("cna", {})
            summary = None
            cvss_score = None
            severity = None
            affected = []
            title = None

            # 1. Parse CVE JSON 5.x structure (CIRCL / CVE v5)
            if cna:
                title = cna.get("title")

                # Descriptions
                descriptions = cna.get("descriptions", [])
                for d in descriptions:
                    if d.get("lang", "").startswith("en") and d.get("value"):
                        summary = d["value"]
                        break
                if not summary and descriptions and descriptions[0].get("value"):
                    summary = descriptions[0]["value"]

                # CVSS Metrics
                metrics = cna.get("metrics", [])
                for m in metrics:
                    for cvss_key in ("cvssV4_0", "cvssV3_1", "cvssV3_0", "cvssV2_0"):
                        if cvss_key in m:
                            cvss_data = m[cvss_key]
                            cvss_score = cvss_data.get("baseScore")
                            severity = cvss_data.get("baseSeverity")
                            break
                    if cvss_score is not None:
                        break

                # Affected products
                for a in cna.get("affected", []):
                    vendor = a.get("vendor", "").strip()
                    product = a.get("product", "").strip()
                    label = f"{vendor} {product}".strip()
                    if label and label not in affected:
                        affected.append(label)

            # 2. Fallback to Legacy CIRCL / CVE 4.x fields
            if not summary:
                summary = data.get("summary")
            if cvss_score is None:
                cvss_score = data.get("cvss")
            if not affected and "vulnerable_configuration" in data:
                vulnerable_configs = data.get("vulnerable_configuration", [])
                for cpe in vulnerable_configs[:4]:
                    parts = cpe.split(":")
                    if len(parts) > 4:
                        lbl = f"{parts[3].capitalize()} {parts[4]}"
                        if lbl not in affected:
                            affected.append(lbl)

            if not summary and not cvss_score and not affected:
                Diagnostics.debug_log(f"[CveProvider] CVE {cve_id} contained no usable intelligence.")
                return None

            if not summary:
                summary = "No detailed synopsis available."

            if not severity:
                if cvss_score is not None:
                    try:
                        score_float = float(cvss_score)
                        if score_float >= 9.0:
                            severity = "CRITICAL"
                        elif score_float >= 7.0:
                            severity = "HIGH"
                        elif score_float >= 4.0:
                            severity = "MEDIUM"
                        else:
                            severity = "LOW"
                    except (ValueError, TypeError):
                        severity = "UNKNOWN"
                else:
                    severity = "UNKNOWN"

            if not title:
                if affected:
                    title = f"{cve_id}: {affected[0]} Vulnerability"
                else:
                    title = f"{cve_id}: Security Vulnerability"

            return {
                "type": "cve",
                "id": cve_id,
                "title": title,
                "summary": summary[:320] + ("..." if len(summary) > 320 else ""),
                "score": cvss_score,
                "severity": severity.upper() if severity else "UNKNOWN",
                "affected": affected,
                "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}"
            }
        except Exception as err:
            Diagnostics.debug_log(f"[CveProvider] Online fetch failed for {cve_id}: {err}")
            return None
