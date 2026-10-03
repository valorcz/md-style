"""
core/providers/ghsa_provider.py
Data provider for GitHub Security Advisories (GHSA) with tiered caching.
"""

import json
import urllib.request
from pathlib import Path
from typing import Dict, Any, Optional
from core.providers.base import BaseProvider
from core.config import GHSA_CACHE_PATH
from core.diagnostics import Diagnostics

class GhsaProvider(BaseProvider):
    name = "ghsa"

    def __init__(self, cache_file: Path = GHSA_CACHE_PATH, allow_online: bool = True):
        super().__init__(cache_file=cache_file, allow_online=allow_online)

    def fetch(self, key: str) -> Optional[Dict[str, Any]]:
        ghsa_id = key.strip()
        if not self.allow_online:
            return None

        url = f"https://api.github.com/advisories/{ghsa_id}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Antigravity-Security-Tooling/1.0 (GitHub Advisory Client)",
                "Accept": "application/vnd.github.v3+json"
            }
        )

        try:
            Diagnostics.debug_log(f"[GhsaProvider] Querying GitHub Advisory API for {ghsa_id}...")
            with urllib.request.urlopen(req, timeout=4) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            title = data.get("summary") or f"{ghsa_id} Security Advisory"
            description = data.get("description", "GitHub Security Advisory record.")
            severity = (data.get("severity") or "HIGH").upper()

            cvss = data.get("cvss", {})
            score = cvss.get("score") if isinstance(cvss, dict) else None

            cve_id = data.get("cve_id")

            return {
                "type": "ghsa",
                "id": ghsa_id,
                "title": title,
                "summary": description[:320] + ("..." if len(description) > 320 else ""),
                "severity": severity,
                "score": score,
                "cve": cve_id,
                "url": f"https://github.com/advisories/{ghsa_id}"
            }
        except Exception as err:
            Diagnostics.debug_log(f"[GhsaProvider] Online fetch failed for {ghsa_id}: {err}")
            return None
