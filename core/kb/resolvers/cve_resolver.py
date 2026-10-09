"""
core/kb/resolvers/cve_resolver.py
Vulnerability intelligence resolver for Common Vulnerabilities and Exposures (CVE).
"""

import re
import json
import urllib.request
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance
from core.config import CVE_CACHE_PATH
from core.diagnostics import Diagnostics

CVE_REGEX = re.compile(r"\b(CVE-\d{4}-\d{4,7})\b", re.IGNORECASE)

class CveResolver(BaseResolver):
    name = "cve"

    def __init__(self, cache_file: Path = CVE_CACHE_PATH):
        self.cache_file = cache_file
        self.cache: dict = {}
        self._load_cache()

    def _load_cache(self):
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def _save_cache(self):
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def can_handle(self, token: str) -> bool:
        return bool(CVE_REGEX.fullmatch(token.strip()))

    def extract_candidates(self, text: str) -> List[str]:
        return list(set(CVE_REGEX.findall(text)))

    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        cve_id = token.strip().upper()

        if not force_refresh and cve_id in self.cache:
            cached_data = self.cache[cve_id]
            return self._to_entity(cve_id, cached_data, from_cache=True)

        if not allow_online:
            fallback_obj = {
                "id": cve_id,
                "title": f"Vulnerability {cve_id}",
                "summary": "External CVE advisory record (offline mode).",
                "cvss": None,
                "severity": "HIGH",
                "cwe": "",
                "references": [{"title": "NVD Entry", "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}"}]
            }
            return self._to_entity(cve_id, fallback_obj, from_cache=False, unresolved=True)

        # Fetch from CIRCL vulnerability lookup API
        url = f"https://vulnerability.circl.lu/api/cve/{cve_id}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Antigravity-Security-Tooling/2.0 (Knowledge Pack Resolver)",
                "Accept": "application/json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                raw = json.loads(resp.read().decode("utf-8"))
            if raw and isinstance(raw, dict):
                cna = raw.get("containers", {}).get("cna", {})
                title = cna.get("title") or cve_id
                summary = ""
                for d in cna.get("descriptions", []):
                    if d.get("lang", "").startswith("en") and d.get("value"):
                        summary = d["value"]
                        break
                if not summary and cna.get("descriptions"):
                    summary = cna["descriptions"][0].get("value", "")

                cvss_score = None
                severity = "HIGH"
                metrics = cna.get("metrics", [])
                for m in metrics:
                    for k in ["cvssV3_1", "cvssV3_0", "cvssV4_0"]:
                        if k in m:
                            cvss_score = m[k].get("baseScore")
                            severity = m[k].get("baseSeverity", "HIGH")
                            break
                    if cvss_score:
                        break

                cwe = ""
                for prob in cna.get("problemTypes", []):
                    for desc in prob.get("descriptions", []):
                        if desc.get("cweId"):
                            cwe = desc.get("cweId")
                            break

                cached_obj = {
                    "id": cve_id,
                    "title": title,
                    "summary": summary,
                    "cvss": cvss_score,
                    "severity": severity,
                    "cwe": cwe,
                    "references": [{"title": "NVD Link", "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}"}]
                }
                self.cache[cve_id] = cached_obj
                self._save_cache()
                return self._to_entity(cve_id, cached_obj, from_cache=False)
        except Exception as e:
            Diagnostics.debug_log(f"CVE lookup failed for {cve_id}: {e}")

        # Fallback offline entry if not found
        fallback_obj = {
            "id": cve_id,
            "title": f"Vulnerability {cve_id}",
            "summary": "External CVE advisory record.",
            "cvss": None,
            "severity": "HIGH",
            "cwe": "",
            "references": [{"title": "NVD Entry", "url": f"https://nvd.nist.gov/vuln/detail/{cve_id}"}]
        }
        return self._to_entity(cve_id, fallback_obj, from_cache=False, unresolved=True)

    def _to_entity(self, cve_id: str, data: dict, from_cache: bool = False, unresolved: bool = False) -> Entity:
        cvss = data.get("cvss")
        badge = f"CVSS {cvss}" if cvss else "CVE RECORD"
        severity = data.get("severity", "HIGH").upper()
        attrs = {}
        if cvss:
            attrs["CVSS Score"] = str(cvss)
        if data.get("cwe"):
            attrs["CWE"] = data["cwe"]

        prov = Provenance(
            source="registry:circl-cve",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="cached" if from_cache else ("unresolved" if unresolved else "resolved"),
            manual_override=False
        )

        return Entity(
            id=cve_id,
            domain="cyber",
            type="cve",
            label=cve_id,
            title=data.get("title") or cve_id,
            severity=severity,
            badge=badge,
            summary=data.get("summary") or "",
            attributes=attrs,
            references=data.get("references", []),
            provenance=prov,
            aliases=[cve_id]
        )
