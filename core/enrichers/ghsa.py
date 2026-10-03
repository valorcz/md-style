"""
core/enrichers/ghsa.py
Enricher for GitHub Security Advisories (GHSA-xxxx-xxxx-xxxx).
"""

import re
from typing import Dict, Any, Optional, Set
from core.enrichers.base import BaseEnricher
from core.providers.ghsa_provider import GhsaProvider
from core.diagnostics import Diagnostics

GHSA_PATTERN = re.compile(r"^GHSA-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}$", re.IGNORECASE)
GHSA_SCAN_PATTERN = re.compile(r"\b(GHSA-[A-Za-z0-9]{4}-[A-Za-z0-9]{4}-[A-Za-z0-9]{4})\b", re.IGNORECASE)

class GhsaEnricher(BaseEnricher):
    name = "ghsa"
    pattern_description = "GitHub Security Advisories (e.g. GHSA-jfh8-c2jp-5v3q)"

    def __init__(self, provider: Optional[GhsaProvider] = None):
        self.provider = provider or GhsaProvider()

    def can_handle(self, token: str) -> bool:
        return bool(GHSA_PATTERN.match(token.strip()))

    def extract_tokens(self, content: str) -> Set[str]:
        return set(GHSA_SCAN_PATTERN.findall(content))

    def enrich(self, token: str) -> Optional[Dict[str, Any]]:
        clean = token.strip()
        res = self.provider.get(clean)
        if res:
            return res
        Diagnostics.warn(f"[GhsaProvider] Advisory '{clean}' could not be resolved from GitHub Advisory database.")
        return {
            "type": "ghsa",
            "id": clean,
            "title": f"{clean}: Unresolved Security Advisory",
            "summary": f"Could not retrieve advisory intelligence for {clean} (record not found in GitHub Advisory database or offline build).",
            "severity": "UNKNOWN",
            "unresolved": True,
            "error_reason": "GHSA not found in GitHub Advisory database or offline build",
            "url": f"https://github.com/advisories/{clean}"
        }

    def get_ast_attributes(self, token: str) -> Dict[str, str]:
        return {
            "class": "ioc cyber-ioc",
            "data-ioc-type": "ghsa",
            "data-ioc-value": token.strip()
        }
