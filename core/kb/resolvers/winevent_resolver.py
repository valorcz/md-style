"""
core/kb/resolvers/winevent_resolver.py
Resolver for Windows Security, System, and Application Event Log IDs.
"""

import re
import json
from pathlib import Path
from typing import Optional, List
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance
from core.config import WIN_EVENTS_DB_PATH
from core.i18n import I18nCatalog

WINEVENT_REGEX = re.compile(r"\b(?:EID|Event\s*ID|Event)\s*[:#]?\s*(\d{4,5})\b", re.IGNORECASE)

CORE_EVENTS = {
    "4624": {
        "title": "An account was successfully logged on",
        "channel": "Security.evtx",
        "severity": "INFO",
        "summary": "Records successful user authentication and logon session creation.",
        "tips": "Inspect LogonType (Type 2=Interactive, Type 3=Network, Type 10=RemoteInteractive/RDP)."
    },
    "4625": {
        "title": "An account failed to log on",
        "channel": "Security.evtx",
        "severity": "MEDIUM",
        "summary": "Records a failed user authentication attempt.",
        "tips": "Inspect Status and SubStatus error codes (0xC000006A: wrong password, 0xC0000064: user does not exist)."
    },
    "4720": {
        "title": "A user account was created",
        "channel": "Security.evtx",
        "severity": "HIGH",
        "summary": "A new local or Active Directory user account was created.",
        "tips": "Verify TargetUserName and SubjectUserName to detect unauthorized backdoor account creation."
    },
    "4726": {
        "title": "A user account was deleted",
        "channel": "Security.evtx",
        "severity": "MEDIUM",
        "summary": "A local or domain user account was deleted.",
        "tips": "Correlate with administrative ticket or incident activity."
    },
    "4728": {
        "title": "A member was added to a security-enabled global group",
        "channel": "Security.evtx",
        "severity": "HIGH",
        "summary": "A user was added to a security global group (e.g., Domain Admins).",
        "tips": "High fidelity indicator of privilege escalation if target group is privileged."
    },
    "4738": {
        "title": "A user account was modified",
        "channel": "Security.evtx",
        "severity": "MEDIUM",
        "summary": "Attributes of a user account were altered (password reset, account enabled/disabled).",
        "tips": "Check UserAccountControl changes."
    },
    "7045": {
        "title": "A new service was installed in the system",
        "channel": "System.evtx",
        "severity": "HIGH",
        "summary": "A new Windows service was registered by Service Control Manager.",
        "tips": "Look for suspicious ImagePath binaries in C:\\Windows\\Temp, PsExec, or Cobalt Strike beacons."
    },
    "1102": {
        "title": "The audit log was cleared",
        "channel": "Security.evtx",
        "severity": "CRITICAL",
        "summary": "The Windows Security audit log file was intentionally cleared.",
        "tips": "Critical anti-forensics indicator. Investigate SubjectUserName immediately."
    },
    "104": {
        "title": "The log file was cleared",
        "channel": "System.evtx",
        "severity": "CRITICAL",
        "summary": "The System log file was cleared.",
        "tips": "Investigate SubjectUserName and corresponding wevtutil command invocations."
    }
}

class WinEventResolver(BaseResolver):
    name = "winevent"

    def __init__(self, db_path: Path = WIN_EVENTS_DB_PATH, catalog: Optional[I18nCatalog] = None):
        self.db_path = db_path
        self.catalog = catalog or I18nCatalog("en")
        self.db = dict(CORE_EVENTS)
        self._load_db()

    def _load_db(self):
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    external = json.load(f)
                    for k, v in external.items():
                        if k not in self.db:
                            self.db[str(k)] = {
                                "title": v.get("name") or v.get("title") or f"Event {k}",
                                "channel": v.get("channel") or "Security.evtx",
                                "severity": v.get("severity", "INFO"),
                                "summary": v.get("description") or v.get("summary") or "",
                                "tips": v.get("investigation_tips", "")
                            }
            except Exception:
                pass

    def can_handle(self, token: str) -> bool:
        t = token.strip()
        m = WINEVENT_REGEX.fullmatch(t)
        if m:
            return True
        # Numeric only check if in DB
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

        if not eid or eid not in self.db:
            if not eid:
                return None
            info = {
                "title": f"Windows Event ID {eid}",
                "channel": "Windows Event Log",
                "severity": "INFO",
                "summary": "Windows operational or security audit event.",
                "tips": ""
            }
        else:
            info = self.db[eid]

        prov = Provenance(
            source="catalog:windows-events",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="resolved",
            manual_override=False
        )

        attrs = {
            "Event ID": eid,
            "Channel": info.get("channel", "Security.evtx")
        }
        if info.get("tips"):
            attrs["Investigation Tips"] = info["tips"]

        return Entity(
            id=f"Event-{eid}",
            domain="cyber",
            type="winevent",
            label=f"Event ID {eid}",
            title=f"Event ID {eid}: {info['title']}",
            severity=info.get("severity", "INFO"),
            badge=f"{self.catalog.t('badges.winevent', default='WIN EVENT')} {eid}",
            summary=info.get("summary", ""),
            attributes=attrs,
            references=[],
            provenance=prov,
            aliases=[f"Event ID {eid}", f"EID {eid}", f"Event {eid}", eid]
        )
