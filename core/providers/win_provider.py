"""
core/providers/win_provider.py
Data provider for Windows Event Log files (.evtx) and security Event IDs.
Features local pre-compiled database, persistent cache tier, fuzzy channel canonicalization,
on-demand online search via MS Learn & UWS, and structured diagnostic reporting for missing indicators.
"""

import json
import re
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Dict, Any, Optional

from core.providers.base import BaseProvider
from core.config import WIN_EVENTS_DB_PATH, WIN_EVENTS_CACHE_PATH
from core.diagnostics import Diagnostics

# Common forensic shorthand aliases for standard Windows event log channels
EVTX_SHORTHAND_MAP = {
    "defender": "Microsoft-Windows-Windows Defender/Operational.evtx",
    "windows defender": "Microsoft-Windows-Windows Defender/Operational.evtx",
    "terminalservices": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational.evtx",
    "terminalservices-localsessionmanager": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational.evtx",
    "localsessionmanager": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational.evtx",
    "rdp": "Microsoft-Windows-TerminalServices-LocalSessionManager/Operational.evtx",
    "remoteconnectionmanager": "Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational.evtx",
    "terminalservices-remoteconnectionmanager": "Microsoft-Windows-TerminalServices-RemoteConnectionManager/Operational.evtx",
    "taskscheduler": "Microsoft-Windows-TaskScheduler/Operational.evtx",
    "task scheduler": "Microsoft-Windows-TaskScheduler/Operational.evtx",
    "powershell": "Microsoft-Windows-PowerShell/Operational.evtx",
    "sysmon": "Microsoft-Windows-Sysmon/Operational.evtx",
    "security": "Security.evtx",
    "system": "System.evtx",
    "application": "Application.evtx",
    "dns": "DNS Server.evtx",
    "dns server": "DNS Server.evtx",
    "bam": "Microsoft-Windows-BackgroundActivityModerator/Operational.evtx"
}

class WindowsEventsProvider(BaseProvider):
    name = "windows_events"

    def __init__(
        self,
        db_path: Path = WIN_EVENTS_DB_PATH,
        cache_file: Path = WIN_EVENTS_CACHE_PATH,
        allow_online: bool = True
    ):
        super().__init__(cache_file=cache_file, allow_online=allow_online)
        self.db_path = db_path
        self._db: Dict[str, Any] = {}
        self._load_db()

    def _load_db(self):
        if self.db_path.exists():
            try:
                with open(self.db_path, "r", encoding="utf-8") as f:
                    self._db = json.load(f)
                Diagnostics.debug_log(f"[WindowsEventsProvider] Loaded {len(self._db)} records from {self.db_path}")
            except Exception as err:
                Diagnostics.warn(f"[WindowsEventsProvider] Failed to load {self.db_path}: {err}")
        else:
            Diagnostics.debug_log(f"[WindowsEventsProvider] {self.db_path} does not exist yet.")

    def get(self, key: str) -> Optional[Dict[str, Any]]:
        """Lookup item with strict precedence: Curated Dataset -> Cache -> Online."""
        if not key:
            return None
        clean_key = key.strip()

        # 1. Curated database has absolute priority
        if clean_key in self._db:
            return self._db[clean_key]

        # Check numeric event id in database
        digits = "".join(filter(str.isdigit, clean_key))
        if digits and digits in self._db:
            return self._db[digits]

        # Check evtx shorthand in database
        if clean_key.lower().endswith(".evtx"):
            clean_stem = Path(clean_key).name.replace(".evtx", "").replace(".EVTX", "").lower()
            if clean_stem in EVTX_SHORTHAND_MAP:
                target_key = EVTX_SHORTHAND_MAP[clean_stem]
                if target_key in self._db:
                    return self._db[target_key]

        # 2. Check cache / online fetch via BaseProvider
        return super().get(key)

    def fetch_evtx_online(self, base_name: str) -> Optional[Dict[str, Any]]:
        """Dynamically queries Microsoft Learn Search API for unknown EVTX log documentation."""
        stem = base_name.replace(".evtx", "").replace(".EVTX", "")
        url = f"https://learn.microsoft.com/api/search?search={urllib.parse.quote(stem)}+evtx+windows+event+log&locale=en-us&$top=1"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "md-style-forensics/2.0 (Security Report Generator)", "Accept": "application/json"}
        )
        try:
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("results", [])
                if results:
                    top = results[0]
                    title = top.get("title", f"{stem} Event Log")
                    summary = top.get("description", f"Windows telemetry log repository for {stem}.")
                    doc_url = top.get("url", f"https://learn.microsoft.com/en-us/windows/win32/eventlog/event-logging")
                    rec = {
                        "type": "evtx",
                        "id": base_name,
                        "title": title,
                        "channel": stem,
                        "role": summary[:300],
                        "url": doc_url,
                        "source": "Microsoft Learn (On-Demand Fetch)"
                    }
                    Diagnostics.info(f"[WindowsEventsProvider] Dynamically resolved EVTX log '{base_name}': '{title}'")
                    return rec
        except Exception as e:
            Diagnostics.debug_log(f"[WindowsEventsProvider] Online query for EVTX '{base_name}' failed: {e}")
        return None

    def fetch_online(self, digits: str) -> Optional[Dict[str, Any]]:
        """Attempts on-demand lookup against Ultimate Windows Security Encyclopedia and MS Learn."""
        # 1. Primary query: Ultimate Windows Security Encyclopedia
        url = f"https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventid={digits}"
        req = urllib.request.Request(
            url,
            headers={"User-Agent": "md-style-forensics/2.0 (Security Report Generator)"}
        )
        try:
            with urllib.request.urlopen(req, timeout=3.5) as resp:
                if resp.status == 200:
                    html = resp.read().decode("utf-8", errors="ignore")
                    m_title = re.search(r"<title>\s*Windows Security Log Event ID\s*\d+\s*-\s*([^<]+)</title>", html, re.I)
                    if not m_title:
                        m_title = re.search(r"<title>\s*Event ID\s*\d+\s*-\s*([^<]+)</title>", html, re.I)

                    if m_title:
                        title = m_title.group(1).strip()
                        summary = f"Audit telemetry event for Windows Security Event ID {digits}: {title}"
                        for line in html.splitlines():
                            clean_line = re.sub(r"<[^>]+>", "", line).strip()
                            if clean_line and len(clean_line) > 30 and ("description" in clean_line.lower() or "audit" in clean_line.lower() or "event" in clean_line.lower()):
                                if "encyclopedia" not in clean_line.lower() and "copyright" not in clean_line.lower():
                                    summary = clean_line[:240]
                                    break

                        rec = {
                            "type": "eventid",
                            "id": digits,
                            "title": title,
                            "channel": "Security",
                            "category": "Windows Audit Telemetry",
                            "severity": "AUDIT EVENT",
                            "summary": summary,
                            "url": url,
                            "source": "Ultimate Windows Security (On-Demand Fetch)"
                        }
                        Diagnostics.info(f"[WindowsEventsProvider] Dynamically fetched online record for Event ID {digits}: '{title}'")
                        return rec
        except Exception as e:
            Diagnostics.debug_log(f"[WindowsEventsProvider] UWS query for Event ID {digits} failed: {e}")

        # 2. Secondary fallback query: Microsoft Learn Search API
        try:
            learn_url = f"https://learn.microsoft.com/api/search?search=windows+event+id+{digits}&locale=en-us&$top=1"
            learn_req = urllib.request.Request(
                learn_url,
                headers={"User-Agent": "md-style-forensics/2.0", "Accept": "application/json"}
            )
            with urllib.request.urlopen(learn_req, timeout=3.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                results = data.get("results", [])
                if results:
                    top = results[0]
                    title = top.get("title", f"Windows Event ID {digits}")
                    summary = top.get("description", f"Microsoft Windows telemetry audit record for Event ID {digits}.")
                    rec = {
                        "type": "eventid",
                        "id": digits,
                        "title": title,
                        "channel": "Security/System",
                        "category": "Windows Audit Telemetry",
                        "severity": "AUDIT EVENT",
                        "summary": summary[:240],
                        "url": top.get("url", f"https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/event-{digits}"),
                        "source": "Microsoft Learn (On-Demand Fetch)"
                    }
                    Diagnostics.info(f"[WindowsEventsProvider] Dynamically fetched MS Learn record for Event ID {digits}: '{title}'")
                    return rec
        except Exception as e:
            Diagnostics.debug_log(f"[WindowsEventsProvider] MS Learn query for Event ID {digits} failed: {e}")

        return None

    def fetch(self, key: str) -> Optional[Dict[str, Any]]:
        clean_key = key.strip()

        # 1. Primary dataset check
        if clean_key in self._db:
            return self._db[clean_key]

        # 2. Check evtx file names
        if clean_key.lower().endswith(".evtx"):
            base = Path(clean_key).name
            if base in self._db:
                return self._db[base]
            if base in self._memory_cache:
                return self._memory_cache[base]

            # Fuzzy shorthand matching
            clean_stem = base.replace(".evtx", "").replace(".EVTX", "").lower()
            if clean_stem in EVTX_SHORTHAND_MAP:
                target_key = EVTX_SHORTHAND_MAP[clean_stem]
                if target_key in self._db:
                    return self._db[target_key]

            # Substring match against database keys
            for k, v in self._db.items():
                if k.lower().endswith(".evtx"):
                    k_stem = k.replace(".evtx", "").lower()
                    if clean_stem in k_stem or k_stem.endswith(clean_stem):
                        return v

            # On-demand online search for unknown EVTX
            if self.allow_online:
                fetched = self.fetch_evtx_online(base)
                if fetched:
                    return fetched

            # Unresolved fallback
            Diagnostics.warn(
                f"[WindowsEventsProvider] EVTX log file '{base}' could not be identified or resolved."
            )
            return {
                "type": "evtx",
                "id": base,
                "title": f"Windows Event Log ({base})",
                "channel": base.replace(".evtx", ""),
                "role": f"Uncataloged Windows Event Log binary repository ({base}).",
                "unresolved": True,
                "error_reason": "Log channel not recognized in Windows telemetry catalogs",
                "url": f"https://www.google.com/search?q={base}+windows+event+log"
            }

        # 3. Numeric Event ID lookup
        digits = "".join(filter(str.isdigit, clean_key))
        if digits:
            if digits in self._db:
                return self._db[digits]

            # 4. Check persistent cache via memory cache
            if digits in self._memory_cache:
                return self._memory_cache[digits]

            # 5. On-demand online fetching
            if self.allow_online:
                fetched = self.fetch_online(digits)
                if fetched:
                    return fetched

            # 6. Structured fallback warning if not found
            Diagnostics.warn(
                f"[WindowsEventsProvider] Windows Event ID '{digits}' not found in database or online sources. Generating fallback record."
            )
            return {
                "type": "eventid",
                "id": digits,
                "title": f"Event ID {digits}",
                "channel": "Security/System",
                "category": "Windows Audit Telemetry",
                "severity": "AUDIT EVENT",
                "summary": f"Audit telemetry record for Windows Event ID {digits}.",
                "unresolved": True,
                "error_reason": "Event ID not found in security encyclopedias",
                "url": f"https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventid={digits}"
            }

        return None
