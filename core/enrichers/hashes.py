"""
core/enrichers/hashes.py
Enricher and classifier for cryptographic hashes (MD5, SHA-1, SHA-256, SHA-512) and hex tokens.
"""

import re
from typing import Dict, Any, Optional, Set
from core.enrichers.base import BaseEnricher

HASH_PATTERN = re.compile(r"^(?:0x)?([a-fA-F0-9]{32}|[a-fA-F0-9]{40}|[a-fA-F0-9]{64}|[a-fA-F0-9]{128})$")

class HashEnricher(BaseEnricher):
    name = "hashes"
    pattern_description = "Cryptographic Hashes & Artifact Fingerprints (MD5, SHA-1, SHA-256)"

    def can_handle(self, token: str) -> bool:
        return bool(HASH_PATTERN.match(token.strip()))

    def extract_tokens(self, content: str) -> Set[str]:
        tokens = set()
        for match in re.finditer(r"\b([a-fA-F0-9]{32}|[a-fA-F0-9]{64})\b", content):
            tokens.add(match.group(1))
        return tokens

    def enrich(self, token: str) -> Optional[Dict[str, Any]]:
        clean = token.strip()
        length = len(clean)
        algo = "MD5" if length == 32 else "SHA-1" if length == 40 else "SHA-256" if length == 64 else "SHA-512" if length == 128 else "HASH"
        return {
            "type": "hash",
            "id": clean,
            "title": f"{algo} Artifact Hash",
            "summary": f"Cryptographic {algo} digest ({length} characters).",
            "algorithm": algo,
            "length": f"{length} CHARS",
            "url": f"https://www.virustotal.com/gui/file/{clean}"
        }

    def get_ast_attributes(self, token: str) -> Dict[str, str]:
        return {
            "class": "hash cyber-ioc",
            "data-ioc-type": "hash",
            "data-ioc-value": token.strip()
        }
