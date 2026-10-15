"""
core/kb/resolvers/ghsa_resolver.py
Vulnerability intelligence resolver for GitHub Security Advisories (GHSA).
Fetches from official GitHub Advisory REST API with persistent disk caching.
"""

import re
import json
import urllib.request
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance
from core.config import GHSA_CACHE_PATH
from core.diagnostics import Diagnostics
from core.i18n import I18nCatalog

GHSA_REGEX = re.compile(r"\b(GHSA-[2-9a-kmnp-z]{4}-[2-9a-kmnp-z]{4}-[2-9a-kmnp-z]{4})\b", re.IGNORECASE)

class GhsaResolver(BaseResolver):
    name = "ghsa"

    def __init__(self, cache_file: Path = GHSA_CACHE_PATH, catalog: Optional[I18nCatalog] = None):
        self.cache_file = cache_file
        self.catalog = catalog or I18nCatalog("en")
        self.cache: Dict[str, Any] = {}
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
        return bool(GHSA_REGEX.fullmatch(token.strip()))

    def extract_candidates(self, text: str) -> List[str]:
        return list(set(GHSA_REGEX.findall(text)))

    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        ghsa_id = token.strip().upper()

        if not force_refresh and ghsa_id in self.cache:
            return self._to_entity(ghsa_id, self.cache[ghsa_id], source="cache:ghsa")

        if not allow_online:
            fallback_data = {
                "id": ghsa_id,
                "summary": f"GitHub Security Advisory {ghsa_id}",
                "description": "Advisory details unretrieved in offline mode.",
                "severity": "HIGH",
                "cve_id": None,
                "cvss": {},
                "cwes": [],
                "vulnerabilities": []
            }
            return self._to_entity(ghsa_id, fallback_data, source="offline:fallback", unresolved=True)

        url = f"https://api.github.com/advisories/{ghsa_id}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Antigravity-Security-Tooling/2.0 (GHSA Resolver)",
                "Accept": "application/vnd.github.v3+json"
            }
        )

        try:
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            if data and isinstance(data, dict):
                self.cache[ghsa_id] = data
                self._save_cache()
                return self._to_entity(ghsa_id, data, source="api:github-advisory")
        except Exception as e:
            Diagnostics.debug_log(f"GHSA lookup failed for {ghsa_id}: {e}")

        # Fallback record
        fallback_data = {
            "id": ghsa_id,
            "summary": f"Security Advisory {ghsa_id}",
            "description": "Record indexed from source document.",
            "severity": "HIGH",
            "cve_id": None,
            "cvss": {},
            "cwes": [],
            "vulnerabilities": []
        }
        return self._to_entity(ghsa_id, fallback_data, source="fallback:ghsa", unresolved=True)

    def _to_entity(self, ghsa_id: str, data: Dict[str, Any], source: str, unresolved: bool = False) -> Entity:
        title = data.get("summary") or f"{ghsa_id} Advisory"
        description = data.get("description") or ""
        severity = (data.get("severity") or "HIGH").upper()
        cve_id = data.get("cve_id")

        cvss_data = data.get("cvss") or {}
        cvss_score = cvss_data.get("score") if isinstance(cvss_data, dict) else None
        cvss_vector = cvss_data.get("vector_string") if isinstance(cvss_data, dict) else None

        cwes = []
        for cwe_item in data.get("cwes", []):
            if isinstance(cwe_item, dict) and cwe_item.get("cwe_id"):
                cwes.append(cwe_item["cwe_id"])
            elif isinstance(cwe_item, str):
                cwes.append(cwe_item)

        vuln_pkgs = []
        for v in data.get("vulnerabilities", []):
            pkg = v.get("package", {}).get("name") if isinstance(v.get("package"), dict) else None
            eco = v.get("package", {}).get("ecosystem") if isinstance(v.get("package"), dict) else None
            patched = v.get("first_patched_version")
            if pkg:
                vuln_pkgs.append(f"{eco or 'pkg'}:{pkg}" + (f" (fixed: {patched})" if patched else ""))

        badge_text = f"CVSS {cvss_score}" if cvss_score else self.catalog.t("badges.ghsa", default="GHSA ADVISORY")

        relationships = []
        if cve_id:
            relationships.append({"target": cve_id, "type": "cve", "relation": "corresponds_to"})

        references = [{"title": "GitHub Advisory Link", "url": f"https://github.com/advisories/{ghsa_id}"}]
        for ref in data.get("references", []):
            if isinstance(ref, dict) and ref.get("url"):
                references.append({"title": ref.get("url"), "url": ref["url"]})
            elif isinstance(ref, str) and ref.startswith("http"):
                references.append({"title": ref, "url": ref})

        prov = Provenance(
            source=source,
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="unresolved" if unresolved else "resolved",
            manual_override=False
        )

        metrics = {}
        if cvss_score is not None:
            metrics["cvss_score"] = cvss_score
        if cvss_vector:
            metrics["cvss_vector"] = cvss_vector

        classification = {
            "cwes": cwes,
            "ecosystems": list(set([v.split(":")[0] for v in vuln_pkgs if ":" in v]))
        }

        details = {
            "Associated CVE": cve_id or "None",
            "Affected Packages": ", ".join(vuln_pkgs) if vuln_pkgs else "Not specified",
            "CWE Identifiers": ", ".join(cwes) if cwes else "None"
        }

        return Entity(
            id=ghsa_id,
            domain="cyber",
            type="ghsa",
            label=ghsa_id,
            title=title,
            severity=severity,
            badge=badge_text,
            summary=description[:400] + ("..." if len(description) > 400 else "") if description else title,
            attributes={
                "CVE": cve_id or "N/A",
                "Severity": severity,
                "CVSS": str(cvss_score) if cvss_score else "N/A",
                "Packages": ", ".join(vuln_pkgs[:3]) if vuln_pkgs else "N/A"
            },
            metrics=metrics,
            classification=classification,
            details=details,
            relationships=relationships,
            references=references[:5],
            provenance=prov,
            aliases=[ghsa_id] + ([cve_id] if cve_id else [])
        )
