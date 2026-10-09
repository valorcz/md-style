"""
core/kb/resolvers/mitre_resolver.py
Resolver for MITRE ATT&CK techniques, tactics, and sub-techniques (e.g. T1003, T1003.001).
"""

import re
from typing import Optional, List
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance

MITRE_TECHNIQUE_RE = re.compile(r"\b(T\d{4}(?:\.\d{3})?)\b")

# Well-known MITRE ATT&CK techniques catalog
TECHNIQUES_CATALOG = {
    "T1003": {
        "title": "OS Credential Dumping",
        "tactic": "Credential Access",
        "summary": "Adversaries may attempt to dump credentials to obtain account login and credential material.",
        "url": "https://attack.mitre.org/techniques/T1003/"
    },
    "T1003.001": {
        "title": "OS Credential Dumping: LSASS Memory",
        "tactic": "Credential Access",
        "summary": "Adversaries may attempt to access credential material stored in the process memory of the Local Security Authority Subsystem Service (LSASS).",
        "url": "https://attack.mitre.org/techniques/T1003/001/"
    },
    "T1003.002": {
        "title": "OS Credential Dumping: Security Account Manager",
        "tactic": "Credential Access",
        "summary": "Adversaries may attempt to extract credential material from the Security Account Manager (SAM) database.",
        "url": "https://attack.mitre.org/techniques/T1003/002/"
    },
    "T1003.006": {
        "title": "OS Credential Dumping: DCSync",
        "tactic": "Credential Access",
        "summary": "Adversaries may simulate the behavior of a Domain Controller via directory replication services (DRS) to retrieve password hashes.",
        "url": "https://attack.mitre.org/techniques/T1003/006/"
    },
    "T1059": {
        "title": "Command and Scripting Interpreter",
        "tactic": "Execution",
        "summary": "Adversaries may abuse command and script interpreters to execute commands, scripts, or binaries.",
        "url": "https://attack.mitre.org/techniques/T1059/"
    },
    "T1059.001": {
        "title": "Command and Scripting Interpreter: PowerShell",
        "tactic": "Execution",
        "summary": "Adversaries may abuse PowerShell commands and scripts for execution and evasion.",
        "url": "https://attack.mitre.org/techniques/T1059/001/"
    },
    "T1078": {
        "title": "Valid Accounts",
        "tactic": "Defense Evasion / Initial Access",
        "summary": "Adversaries may obtain and abuse credentials of existing accounts as a means of gaining initial access, persistence, or privilege escalation.",
        "url": "https://attack.mitre.org/techniques/T1078/"
    },
    "T1562": {
        "title": "Impair Defenses",
        "tactic": "Defense Evasion",
        "summary": "Adversaries may maliciously modify system components to hinder defensive visibility or security controls.",
        "url": "https://attack.mitre.org/techniques/T1562/"
    },
    "T1562.001": {
        "title": "Impair Defenses: Disable or Modify Tools",
        "tactic": "Defense Evasion",
        "summary": "Adversaries may modify or disable security software (such as Windows Defender or EDR sensors) to avoid detection.",
        "url": "https://attack.mitre.org/techniques/T1562/001/"
    },
    "T1070": {
        "title": "Indicator Removal",
        "tactic": "Defense Evasion",
        "summary": "Adversaries may delete or alter event logs, audit records, or security system configurations.",
        "url": "https://attack.mitre.org/techniques/T1070/"
    },
    "T1070.001": {
        "title": "Indicator Removal: Clear Windows Event Logs",
        "tactic": "Defense Evasion",
        "summary": "Adversaries may clear Windows Event Logs using wevtutil or PowerShell to cover their tracks.",
        "url": "https://attack.mitre.org/techniques/T1070/001/"
    }
}

class MitreResolver(BaseResolver):
    name = "mitre"

    def can_handle(self, token: str) -> bool:
        return bool(MITRE_TECHNIQUE_RE.fullmatch(token.strip()))

    def extract_candidates(self, text: str) -> List[str]:
        return list(set(MITRE_TECHNIQUE_RE.findall(text)))

    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        tid = token.strip().upper()
        info = TECHNIQUES_CATALOG.get(tid)

        if not info and "." in tid:
            parent_id = tid.split(".")[0]
            if parent_id in TECHNIQUES_CATALOG:
                parent = TECHNIQUES_CATALOG[parent_id]
                info = {
                    "title": f"{parent['title']} (Sub-technique {tid})",
                    "tactic": parent["tactic"],
                    "summary": f"Sub-technique under {parent['title']}.",
                    "url": f"https://attack.mitre.org/techniques/{tid.replace('.', '/')}/"
                }

        if not info:
            info = {
                "title": f"ATT&CK Technique {tid}",
                "tactic": "Adversary TTP",
                "summary": "Adversary tactic or technique cataloged in MITRE ATT&CK framework.",
                "url": f"https://attack.mitre.org/techniques/{tid.replace('.', '/')}/"
            }

        prov = Provenance(
            source="catalog:mitre-attack",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="resolved",
            manual_override=False
        )

        return Entity(
            id=tid,
            domain="cyber",
            type="mitre",
            label=tid,
            title=f"{tid}: {info['title']}",
            severity="HIGH",
            badge=f"MITRE {info['tactic'].upper()}",
            summary=info["summary"],
            attributes={
                "Framework": "MITRE ATT&CK",
                "Tactic": info["tactic"],
                "Technique ID": tid
            },
            references=[{"title": "MITRE ATT&CK Matrix", "url": info["url"]}],
            provenance=prov,
            aliases=[tid]
        )
