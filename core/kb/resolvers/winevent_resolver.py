"""
core/kb/resolvers/winevent_resolver.py
Resolver for Windows Security, System, and Application Event Log IDs.
Loads authoritative event metadata directly from data/windows-events.json (SSOT)
and links events bi-directionally to their hosting .evtx channels and MITRE ATT&CK techniques.
"""

import re
import json
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance
from core.config import WIN_EVENTS_DB_PATH, WIN_EVENTS_CACHE_PATH
from core.i18n import I18nCatalog
from core.diagnostics import Diagnostics

WINEVENT_REGEX = re.compile(r"\b(?:EID|Event\s*ID|Event)\s*[:#]?\s*(\d{1,5})\b", re.IGNORECASE)
MITRE_TID_REGEX = re.compile(r"\b(T\d{4}(?:\.\d{3})?)\b")


class WinEventResolver(BaseResolver):
    name = "winevent"

    def __init__(
        self,
        db_path: Optional[Path] = None,
        catalog: Optional[I18nCatalog] = None
    ):
        if db_path is not None:
            self.db_path = db_path
        elif WIN_EVENTS_CACHE_PATH.exists():
            self.db_path = WIN_EVENTS_CACHE_PATH
        else:
            self.db_path = WIN_EVENTS_DB_PATH

        self.catalog = catalog or I18nCatalog("en")
        self.db: Dict[str, Dict[str, Any]] = {}
        self._load_db()

    def _load_db(self) -> None:
        if not self.db_path.exists():
            return

        try:
            with open(self.db_path, "r", encoding="utf-8") as f:
                external = json.load(f)
        except Exception as e:
            Diagnostics.debug_log(f"Failed to read windows events database: {e}")
            return

        for k, v in external.items():
            if not isinstance(v, dict):
                continue
            is_eid = v.get("type") == "eventid" or str(k).isdigit()
            if not is_eid:
                continue

            tips = v.get("investigation_tips") or v.get("tips") or ""
            if isinstance(tips, list):
                tips_str = " | ".join(tips)
            else:
                tips_str = str(tips)

            self.db[str(k)] = {
                "id": str(k),
                "title": v.get("title") or v.get("name") or f"Event {k}",
                "channel": v.get("channel") or "Security",
                "category": v.get("category", ""),
                "severity": self._normalize_severity(v.get("severity", "INFO")),
                "summary": v.get("summary") or v.get("description") or "",
                "tips": tips_str,
                "raw_tips": v.get("investigation_tips") or v.get("tips") or [],
                "key_fields": v.get("key_fields", []),
                "mitre": v.get("mitre", []),
                "attacker_behavior": v.get("attacker_behavior", []),
                "benign_causes": v.get("benign_causes", []),
                "url": v.get("url", f"https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventid={k}")
            }

    @staticmethod
    def _normalize_severity(sev: str) -> str:
        s = str(sev).upper().strip()
        if "CRIT" in s:
            return "CRITICAL"
        if "HIGH" in s or "ERROR" in s:
            return "HIGH"
        if "MED" in s or "WARN" in s:
            return "MEDIUM"
        if "LOW" in s:
            return "LOW"
        return "INFO"

    def can_handle(self, token: str) -> bool:
        t = token.strip()
        m = WINEVENT_REGEX.fullmatch(t)
        if m:
            return True
        if t.isdigit() and t in self.db:
            return True
        return False

    def extract_candidates(self, text: str) -> List[str]:
        results = []
        for m in WINEVENT_REGEX.finditer(text):
            results.append(m.group(0))
        return list(set(results))

    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        t = token.strip()
        eid = None
        m = WINEVENT_REGEX.search(t)
        if m:
            eid = m.group(1)
        elif t.isdigit():
            eid = t

        if not eid:
            return None

        unresolved = False
        if eid in self.db:
            info = self.db[eid]
        else:
            unresolved = True
            info = {
                "id": eid,
                "title": f"Windows Event ID {eid}",
                "channel": "Windows Event Log",
                "category": "Operational Telemetry",
                "severity": "INFO",
                "summary": f"Windows operational or security audit event {eid}.",
                "tips": "",
                "key_fields": [],
                "mitre": [],
                "attacker_behavior": [],
                "benign_causes": [],
                "url": f"https://learn.microsoft.com/en-us/search/?terms=Event+{eid}+windows"
            }

        prov = Provenance(
            source="catalog:windows-events",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="unresolved" if unresolved else "resolved",
            manual_override=False
        )

        raw_channel = info.get("channel", "Security")
        evtx_target = raw_channel if raw_channel.lower().endswith(".evtx") else f"{raw_channel}.evtx"
        relationships: List[Dict[str, Any]] = [
            {"target": evtx_target, "type": "evtx", "relation": "logged_in_channel"}
        ]

        # Extract and cross-link MITRE ATT&CK techniques
        for mitre_item in info.get("mitre", []):
            match = MITRE_TID_REGEX.search(str(mitre_item))
            if match:
                tid = match.group(1).upper()
                relationships.append({"target": tid, "type": "mitre", "relation": "detects_technique"})

        details: Dict[str, Any] = {
            "Event Log Channel": raw_channel,
            "Investigation Tips": info.get("tips") or "Correlate with process creation and user logon telemetry."
        }
        if info.get("category"):
            details["Audit Category"] = info["category"]
        if info.get("key_fields"):
            details["Key Event Fields"] = ", ".join(str(f) for f in info["key_fields"])
        if info.get("attacker_behavior"):
            details["Attacker Behavior"] = " | ".join(str(b) for b in info["attacker_behavior"][:3])

        references = []
        if info.get("url"):
            references.append({"title": "Event Encyclopedia Reference", "url": info["url"]})

        return Entity(
            id=f"Event-{eid}",
            domain="cyber",
            type="winevent",
            label=f"Event ID {eid}",
            title=f"Event ID {eid}: {info['title']}",
            severity=info.get("severity", "INFO"),
            badge=f"{self.catalog.t('badges.winevent', default='WIN EVENT')} {eid}",
            summary=info.get("summary", ""),
            attributes=details,
            metrics={"event_id": int(eid) if eid.isdigit() else eid},
            classification={
                "channel": raw_channel,
                "category": info.get("category", ""),
                "log_type": "Windows Event Log"
            },
            details=details,
            relationships=relationships,
            references=references,
            provenance=prov,
            aliases=[f"Event ID {eid}", f"EID {eid}", f"Event {eid}", eid]
        )
