"""
core/enrichers/mitre.py
Enricher for MITRE ATT&CK enterprise techniques (Txxxx, Txxxx.yyy) and tactics (TAxxxx).
"""

import re
from typing import Dict, Any, Optional, Set
from core.enrichers.base import BaseEnricher
from core.providers.mitre_provider import MitreProvider

MITRE_PATTERN = re.compile(r"^(?:T\d{4}(?:\.\d{3})?|TA\d{4})$", re.IGNORECASE)
MITRE_SCAN_PATTERN = re.compile(r"\b(T\d{4}(?:\.\d{3})?|TA\d{4})\b")

class MitreEnricher(BaseEnricher):
    name = "mitre"
    pattern_description = "MITRE ATT&CK Techniques & Tactics (e.g. T1059, T1059.001, TA0002)"

    def __init__(self, provider: Optional[MitreProvider] = None):
        self.provider = provider or MitreProvider()

    def can_handle(self, token: str) -> bool:
        return bool(MITRE_PATTERN.match(token.strip()))

    def extract_tokens(self, content: str) -> Set[str]:
        return set(MITRE_SCAN_PATTERN.findall(content))

    def enrich(self, token: str) -> Optional[Dict[str, Any]]:
        clean = token.strip().upper()
        res = self.provider.get(clean)
        if res:
            return res
        return {
            "type": "mitre",
            "id": clean,
            "name": f"MITRE ATT&CK Technique {clean}",
            "summary": "Enterprise adversary technique.",
            "url": f"https://attack.mitre.org/techniques/{clean.replace('.', '/')}/"
        }

    def get_ast_attributes(self, token: str) -> Dict[str, str]:
        return {
            "class": "mitre-pill cyber-ioc",
            "data-ioc-type": "mitre",
            "data-ioc-value": token.strip()
        }
