"""
core/enrichers/windows_events.py
Enricher for Windows Event Log files (.evtx) and security Event IDs (Security, System, Sysmon, PowerShell, Defender).
Supports singular Event IDs (Event ID 4624, EID 5000) and compound multi-ID references (EID 5000, 5001 and 600).
"""

import re
from pathlib import Path
from typing import Dict, Any, Optional, Set, List
from core.enrichers.base import BaseEnricher
from core.providers.win_provider import WindowsEventsProvider

COMMON_SECURITY_EIDS = {
    "4624", "4625", "4672", "4688", "4697", "7045", "4720", "4726",
    "4728", "4732", "4738", "4768", "4769", "4771", "4776", "1102",
    "104", "4104", "4103", "5000", "5001", "5004", "5007", "1116", "1117",
    "600", "4696", "1", "3", "7", "8", "10", "11", "12", "13", "21", "22", "23", "24", "25", "28"
}

# Matches "Event ID 4624", "EID 5000", "Event IDs: 5000, 5001 and 600", "EID 21/23", etc.
COMPOUND_EID_PATTERN = re.compile(
    r"\b((?:Event\s*IDs?|EIDs?)\s*:?\s*\d+(?:[\s,\/]+(?:and|&|a)?\s*\d+)*)\b",
    re.IGNORECASE
)

class WindowsEventsEnricher(BaseEnricher):
    name = "windows_events"
    pattern_description = "Windows Event Log files (.evtx) and Event IDs (e.g. Security.evtx, Event ID 4624, EID 5000, 5001 and 600)"

    def __init__(self, provider: Optional[WindowsEventsProvider] = None):
        self.provider = provider or WindowsEventsProvider()

    def can_handle(self, token: str) -> bool:
        clean = token.strip()
        if clean.lower().endswith(".evtx"):
            return True

        lower = clean.lower()
        if lower.startswith("event") or lower.startswith("eid"):
            # Check if it has at least one number
            if any(char.isdigit() for char in clean):
                return True

        if clean.isdigit():
            if clean in COMMON_SECURITY_EIDS or clean in self.provider._db:
                return True

        return False

    def extract_tokens(self, content: str) -> Set[str]:
        tokens = set()
        # 1. Scan evtx files
        for match in re.finditer(r"\b([A-Za-z0-9_\-\/]+\.evtx)\b", content, re.IGNORECASE):
            tokens.add(match.group(1))

        # 2. Scan compound & singular Event IDs: "EID 5000, 5001 and 600", "Event ID 4624", etc.
        for match in COMPOUND_EID_PATTERN.finditer(content):
            full_match = match.group(1).strip()
            tokens.add(full_match)
            # Also extract individual numbers and standard tokens
            nums = re.findall(r"\d+", full_match)
            for n in nums:
                tokens.add(f"Event ID {n}")
                tokens.add(f"EID {n}")
                tokens.add(n)

        return tokens

    def enrich(self, token: str) -> Optional[Dict[str, Any]]:
        clean = token.strip()

        # Handle .evtx files
        if clean.lower().endswith(".evtx"):
            res = self.provider.get(clean)
            if res:
                return res
            base = Path(clean).name
            channel = base.replace(".evtx", "")
            return {
                "type": "evtx",
                "id": base,
                "title": f"Windows Event Log ({base})",
                "channel": channel,
                "role": "Binary XML Windows Event Log repository.",
                "url": "https://learn.microsoft.com/en-us/windows/win32/eventlog/event-logging"
            }

        # Check for multiple numbers in a compound phrase
        nums = re.findall(r"\d+", clean)
        if len(nums) > 1:
            # Compound token (e.g. "EID 5000, 5001 and 600")
            sub_events = []
            channels = set()
            summaries = []
            has_critical = False

            for n in nums:
                rec = self.provider.get(n)
                if not rec:
                    rec = {
                        "type": "eventid",
                        "id": n,
                        "title": f"Event ID {n}",
                        "channel": "Security/System",
                        "category": "Windows Telemetry",
                        "severity": "AUDIT EVENT",
                        "summary": f"Audit telemetry record for Event ID {n}.",
                        "url": f"https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventid={n}"
                    }
                sub_events.append(rec)
                ch = rec.get("channel", "Security")
                channels.add(ch)
                sev = rec.get("severity", "")
                if "CRITICAL" in sev.upper() or "TAMPER" in sev.upper():
                    has_critical = True
                summaries.append(f"• Event ID {n} ({rec.get('title', 'Event ' + n)}): {rec.get('summary', '')}")

            summary_text = f"Compound reference to {len(nums)} Windows Event IDs ({', '.join(nums)}):\n" + "\n".join(summaries)
            severity = "CRITICAL AUDIT TELEMETRY" if has_critical else "CORRELATED EVENT LOGS"

            return {
                "type": "eventid",
                "id": ", ".join(nums),
                "title": f"Windows Event IDs: {', '.join(nums)}",
                "channel": ", ".join(sorted(channels)),
                "category": "Correlated Event Telemetry",
                "severity": severity,
                "summary": summary_text,
                "events": sub_events,
                "url": sub_events[0].get("url") if sub_events else "https://learn.microsoft.com/en-us/windows/security/threat-protection/auditing/security-auditing-overview"
            }

        # Single Event ID
        digits = nums[0] if nums else "".join(filter(str.isdigit, clean))
        if digits:
            res = self.provider.get(digits)
            if res:
                return res
            return {
                "type": "eventid",
                "id": digits,
                "title": f"Event ID {digits}",
                "channel": "Security",
                "category": "Windows Audit",
                "severity": "AUDIT EVENT",
                "summary": f"Audit telemetry record for Event ID {digits}.",
                "url": f"https://www.ultimatewindowssecurity.com/securitylog/encyclopedia/event.aspx?eventid={digits}"
            }

        return None

    def get_ast_attributes(self, token: str) -> Dict[str, str]:
        clean = token.strip()
        if clean.lower().endswith(".evtx"):
            return {
                "class": "evtx-pill cyber-ioc",
                "data-ioc-type": "evtx",
                "data-ioc-value": clean
            }
        else:
            return {
                "class": "eventid-pill cyber-ioc",
                "data-ioc-type": "eventid",
                "data-ioc-value": clean
            }
