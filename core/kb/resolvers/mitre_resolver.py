"""
core/kb/resolvers/mitre_resolver.py
Resolver for MITRE ATT&CK techniques, tactics, and sub-techniques (e.g. T1003, T1003.001).
Loads authoritative technique metadata directly from data/mitre-attack.json (SSOT).
"""

import re
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance
from core.config import MITRE_DB_PATH, INTEL_CACHE_DIR
from core.i18n import I18nCatalog
from core.diagnostics import Diagnostics

MITRE_TECHNIQUE_RE = re.compile(r"\b(T\d{4}(?:\.\d{3})?)\b")


class MitreResolver(BaseResolver):
    name = "mitre"

    def __init__(
        self,
        db_path: Optional[Path] = None,
        catalog: Optional[I18nCatalog] = None
    ):
        cache_path = INTEL_CACHE_DIR / "mitre-attack.json"
        if db_path is not None:
            self.db_path = db_path
        elif cache_path.exists():
            self.db_path = cache_path
        else:
            self.db_path = MITRE_DB_PATH

        self.catalog = catalog or I18nCatalog("en")
        self.db: Dict[str, Dict[str, Any]] = {}
        self._load_db()

    def _load_db(self) -> None:
        if not self.db_path.exists():
            return

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                self.db = json.load(f)
        except Exception as e:
            Diagnostics.debug_log(f"Failed to read MITRE ATT&CK database: {e}")
            self.db = {}

    def can_handle(self, token: str) -> bool:
        return bool(MITRE_TECHNIQUE_RE.fullmatch(token.strip()))

    def extract_candidates(self, text: str) -> List[str]:
        return list(set(MITRE_TECHNIQUE_RE.findall(text)))

    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        tid = token.strip().upper()
        unresolved = False

        if tid in self.db:
            info = self.db[tid]
        elif "." in tid:
            parent_id = tid.split(".")[0]
            if parent_id in self.db:
                parent = self.db[parent_id]
                info = {
                    "id": tid,
                    "title": f"{parent.get('title', 'Unknown')} (Sub-technique {tid})",
                    "tactic": parent.get("tactic", "Adversary TTP"),
                    "summary": f"Sub-technique under {parent.get('title', parent_id)}.",
                    "platforms": parent.get("platforms", []),
                    "url": f"https://attack.mitre.org/techniques/{tid.replace('.', '/')}/"
                }
            else:
                unresolved = True
                info = {
                    "id": tid,
                    "title": f"ATT&CK Technique {tid}",
                    "tactic": "Adversary TTP",
                    "summary": "Adversary tactic or technique cataloged in MITRE ATT&CK framework.",
                    "platforms": [],
                    "url": f"https://attack.mitre.org/techniques/{tid.replace('.', '/')}/"
                }
        else:
            unresolved = True
            info = {
                "id": tid,
                "title": f"ATT&CK Technique {tid}",
                "tactic": "Adversary TTP",
                "summary": "Adversary tactic or technique cataloged in MITRE ATT&CK framework.",
                "platforms": [],
                "url": f"https://attack.mitre.org/techniques/{tid}/"
            }

        prov = Provenance(
            source="catalog:mitre-attack",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="unresolved" if unresolved else "resolved",
            manual_override=False
        )

        relationships = []
        if "." in tid:
            parent_id = tid.split(".")[0]
            relationships.append({"target": parent_id, "type": "mitre", "relation": "subtechnique_of"})

        tactic = info.get("tactic", "Adversary TTP")
        classification = {
            "tactics": [t.strip() for t in tactic.split("/") if t.strip()],
            "framework": "MITRE ATT&CK Enterprise Matrix"
        }

        details = {
            "Technique Identifier": tid,
            "Primary Tactic": tactic,
            "Detection & Defense Guidance": info.get("summary", "")
        }
        if info.get("platforms"):
            details["Platforms"] = ", ".join(info["platforms"])

        badge_prefix = self.catalog.t("badges.mitre", default="MITRE")
        badge = f"{badge_prefix} {tactic.upper()}" if tactic else badge_prefix

        return Entity(
            id=tid,
            domain="cyber",
            type="mitre",
            label=tid,
            title=f"{tid}: {info.get('title', tid)}",
            severity="HIGH",
            badge=badge,
            summary=info.get("summary", ""),
            attributes={
                "Framework": "MITRE ATT&CK",
                "Tactic": tactic,
                "Technique ID": tid
            },
            metrics={"matrix_version": "v14", "scope": "Enterprise ATT&CK"},
            classification=classification,
            details=details,
            relationships=relationships,
            references=[{"title": "MITRE ATT&CK Matrix", "url": info.get("url", f"https://attack.mitre.org/techniques/{tid}/")}],
            provenance=prov,
            aliases=[tid]
        )
