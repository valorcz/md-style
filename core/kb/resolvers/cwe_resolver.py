"""
core/kb/resolvers/cwe_resolver.py
Weakness intelligence resolver for Common Weakness Enumeration (CWE).
Loads authoritative CWE data from data/cwe.json with runtime caching in ~/.cache/md-style/intel/cwe.json,
rich metrics extraction (Top 25 rank, abstraction layer, CIA impacts, mitigations, platforms),
and automated cross-references to MITRE ATT&CK techniques.
"""

import re
import json
import urllib.request
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance
from core.config import CWE_CACHE_PATH, CWE_DB_PATH
from core.diagnostics import Diagnostics
from core.i18n import I18nCatalog

CWE_REGEX = re.compile(r"\b(CWE-\d{1,5})\b", re.IGNORECASE)


class CweResolver(BaseResolver):
    name = "cwe"

    def __init__(
        self,
        cache_file: Path = CWE_CACHE_PATH,
        db_path: Path = CWE_DB_PATH,
        catalog: Optional[I18nCatalog] = None
    ):
        self.cache_file = cache_file
        self.db_path = db_path
        self.catalog = catalog or I18nCatalog("en")
        self.db: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        # 1. Load bundled authoritative database (data/cwe.json)
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self.db.update(json.load(f))
            except Exception as e:
                Diagnostics.debug_log(f"Failed to read bundled CWE database: {e}")

        # 2. Load runtime user cache (~/.cache/md-style/intel/cwe.json) taking precedence
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    user_cached = json.load(f)
                    for k, v in user_cached.items():
                        if k in self.db and (self.db[k].get("impacts") or self.db[k].get("mitigations") or self.db[k].get("top25_rank")) and not (v.get("impacts") or v.get("mitigations") or v.get("top25_rank")):
                            continue
                        self.db[k] = v
            except Exception:
                pass

    def _save_cache(self) -> None:
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.db, f, indent=2, ensure_ascii=False)
        except Exception as e:
            Diagnostics.debug_log(f"Failed to write CWE cache: {e}")

    def can_handle(self, token: str) -> bool:
        return bool(CWE_REGEX.fullmatch(token.strip()))

    def extract_candidates(self, text: str) -> List[str]:
        return list(set(CWE_REGEX.findall(text)))

    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        cwe_id = token.strip().upper()
        # Extract numeric id
        match = re.search(r"\d+", cwe_id)
        if not match:
            return None
        wid = match.group(0)
        norm_id = f"CWE-{wid}"

        # 1. Check local database / cache
        if norm_id in self.db:
            return self._to_entity(norm_id, self.db[norm_id], from_cache=True)

        if not allow_online:
            # Offline clean fallback
            fallback_data = {
                "id": norm_id,
                "title": f"Weakness {norm_id}",
                "abstraction": "Base",
                "status": "Unknown",
                "summary": f"Common Weakness Enumeration entry {norm_id}.",
                "extended_description": "",
                "scopes": [],
                "impacts": [],
                "mitigations": [],
                "detection_methods": [],
                "platforms": [],
                "capecs": [],
                "mitre_techniques": [],
                "parent_cwes": [],
                "top25_rank": None,
                "url": f"https://cwe.mitre.org/data/definitions/{wid}.html"
            }
            return self._to_entity(norm_id, fallback_data, from_cache=False, unresolved=True)

        # 2. Dynamic online fetch if allowed (via CIRCL or MITRE definitions)
        fetched = self._fetch_online(norm_id, wid)
        if fetched:
            self.db[norm_id] = fetched
            self._save_cache()
            return self._to_entity(norm_id, fetched, from_cache=False)

        # 3. Fallback if fetch failed
        fallback_data = {
            "id": norm_id,
            "title": f"Weakness {norm_id}",
            "abstraction": "Base",
            "status": "Unknown",
            "summary": f"Common Weakness Enumeration entry {norm_id}.",
            "extended_description": "",
            "scopes": [],
            "impacts": [],
            "mitigations": [],
            "detection_methods": [],
            "platforms": [],
            "capecs": [],
            "mitre_techniques": [],
            "parent_cwes": [],
            "top25_rank": None,
            "url": f"https://cwe.mitre.org/data/definitions/{wid}.html"
        }
        return self._to_entity(norm_id, fallback_data, from_cache=False, unresolved=True)

    def _fetch_online(self, norm_id: str, wid: str) -> Optional[Dict[str, Any]]:
        """Queries CIRCL or NVD for dynamic online resolution of obscure CWEs."""
        url = f"https://cwe.mitre.org/data/definitions/{wid}.html"
        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": "Antigravity-Security-Tooling/2.0 (CWE Intelligence Resolver)"}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                if resp.status == 200:
                    html_text = resp.read().decode("utf-8", errors="ignore")
                    title_match = re.search(r"<title>CWE\s*-\s*CWE-\d+:\s*(.*?)(?:\s*\(.*?\))?</title>", html_text, re.IGNORECASE)
                    title = title_match.group(1).strip() if title_match else f"Weakness {norm_id}"
                    return {
                        "id": norm_id,
                        "title": title,
                        "abstraction": "Base",
                        "status": "Published",
                        "summary": f"Canonical weakness {norm_id}: {title}.",
                        "extended_description": "",
                        "scopes": [],
                        "impacts": [],
                        "mitigations": [],
                        "detection_methods": [],
                        "platforms": [],
                        "capecs": [],
                        "mitre_techniques": [],
                        "parent_cwes": [],
                        "top25_rank": None,
                        "url": url
                    }
        except Exception:
            pass
        return None

    def _to_entity(
        self,
        cwe_id: str,
        data: Dict[str, Any],
        from_cache: bool = False,
        unresolved: bool = False
    ) -> Entity:
        name = data.get("title", f"Weakness {cwe_id}")
        summary = data.get("summary", "")
        abstraction = data.get("abstraction", "Base")
        top25_rank = data.get("top25_rank")
        scopes = data.get("scopes", [])
        impacts = data.get("impacts", [])
        mitigations = data.get("mitigations", [])
        detection_methods = data.get("detection_methods", [])
        platforms = data.get("platforms", [])
        mitre_techniques = data.get("mitre_techniques", [])
        parent_cwes = data.get("parent_cwes", [])
        url = data.get("url", f"https://cwe.mitre.org/data/definitions/{cwe_id.replace('CWE-', '')}.html")

        # Determine severity
        if top25_rank and top25_rank <= 10:
            severity = "CRITICAL"
        elif top25_rank and top25_rank <= 25:
            severity = "HIGH"
        elif any(i in ["Execute Unauthorized Code or Commands", "Modify Memory"] for i in impacts):
            severity = "HIGH"
        else:
            severity = "MEDIUM"

        badge = f"TOP 25 #{top25_rank}" if top25_rank else f"CWE {abstraction.upper()}"

        attrs: Dict[str, str] = {
            "Abstraction": abstraction,
            "Framework": "MITRE Common Weakness Enumeration",
        }
        if top25_rank:
            attrs["Top 25 Rank"] = f"2024 Rank #{top25_rank}"
        if scopes:
            attrs["Impact Scope"] = ", ".join(scopes)

        details: Dict[str, Any] = {
            "Weakness Identifier": cwe_id,
            "Weakness Name": name,
            "Abstraction Layer": abstraction,
        }
        if top25_rank:
            details["Top 25 Rank"] = f"MITRE CWE Top 25 (Rank #{top25_rank})"
        if impacts:
            details["Common Consequences"] = " | ".join(impacts)
        if mitigations:
            details["Mitigation Strategy"] = " | ".join(mitigations)
        if detection_methods:
            details["Detection Methods"] = " | ".join(detection_methods)
        if platforms:
            details["Applicable Platforms"] = ", ".join(platforms)

        classification: Dict[str, Any] = {
            "framework": "MITRE CWE",
            "abstraction": abstraction,
        }
        if top25_rank:
            classification["top25_rank"] = top25_rank
        if scopes:
            classification["scopes"] = scopes
        if impacts:
            classification["impacts"] = impacts
        if platforms:
            classification["platforms"] = platforms

        relationships: List[Dict[str, Any]] = []
        for tid in mitre_techniques:
            relationships.append({
                "target": tid,
                "type": "mitre",
                "relation": "exploited_via"
            })
        for pid in parent_cwes:
            relationships.append({
                "target": pid,
                "type": "cwe",
                "relation": "child_of"
            })

        prov = Provenance(
            source="catalog:mitre-cwe",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="cached" if from_cache else ("unresolved" if unresolved else "resolved"),
            manual_override=False
        )

        return Entity(
            id=cwe_id,
            domain="cyber",
            type="cwe",
            label=cwe_id,
            title=f"{cwe_id}: {name}" if not name.startswith("CWE-") else name,
            severity=severity,
            badge=badge,
            summary=summary,
            attributes=attrs,
            metrics={"abstraction": abstraction, "top25_rank": top25_rank},
            classification=classification,
            details=details,
            relationships=relationships,
            references=[{"title": f"MITRE CWE {cwe_id} Definition", "url": url}],
            provenance=prov,
            aliases=[cwe_id]
        )
