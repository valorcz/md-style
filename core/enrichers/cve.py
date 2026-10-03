"""
core/enrichers/cve.py
Enricher for Common Vulnerabilities and Exposures (CVE-YYYY-NNNN+).
"""

import re
from typing import Dict, Any, Optional, Set
from core.enrichers.base import BaseEnricher
from core.providers.cve_provider import CveProvider
from core.diagnostics import Diagnostics

CVE_PATTERN = re.compile(r"^CVE-\d{4}-\d{4,}$", re.IGNORECASE)
CVE_SCAN_PATTERN = re.compile(r"\b(CVE-\d{4}-\d{4,})\b", re.IGNORECASE)

class CveEnricher(BaseEnricher):
    name = "cve"
    pattern_description = "CVE Vulnerability Identifiers (e.g. CVE-2024-21762)"

    def __init__(self, provider: Optional[CveProvider] = None):
        self.provider = provider or CveProvider()

    def can_handle(self, token: str) -> bool:
        return bool(CVE_PATTERN.match(token.strip()))

    def extract_tokens(self, content: str) -> Set[str]:
        return set(CVE_SCAN_PATTERN.findall(content))

    def enrich(self, token: str) -> Optional[Dict[str, Any]]:
        clean = token.strip().upper()
        res = self.provider.get(clean)
        if res:
            return res
        Diagnostics.warn(f"[CveProvider] Vulnerability '{clean}' could not be resolved from CIRCL / NVD.")
        return {
            "type": "cve",
            "id": clean,
            "title": f"{clean}: Unresolved Vulnerability Record",
            "summary": f"Could not retrieve vulnerability intelligence for {clean} (record not found in CIRCL / NVD or offline build).",
            "severity": "UNKNOWN",
            "unresolved": True,
            "error_reason": "CVE not found in vulnerability databases or offline build",
            "url": f"https://nvd.nist.gov/vuln/detail/{clean}"
        }

    def get_ast_attributes(self, token: str) -> Dict[str, str]:
        return {
            "class": "ioc cyber-ioc",
            "data-ioc-type": "cve",
            "data-ioc-value": token.strip()
        }
