"""
core/enrichers/custom.py
Enricher for custom document and case-specific knowledge entries.
"""

from typing import Dict, Any, Optional, Set
from .base import BaseEnricher
from core.knowledge import KnowledgeManager

class CustomKnowledgeEnricher(BaseEnricher):
    name: str = "custom"
    pattern_description: str = "Custom case entities and investigator annotations"

    def __init__(self, manager: KnowledgeManager):
        self.manager = manager

    def can_handle(self, token: str) -> bool:
        return self.manager.find_entry(token) is not None

    def extract_tokens(self, content: str) -> Set[str]:
        found: Set[str] = set()
        if not content:
            return found

        for entry in self.manager.entries:
            # 1. Exact matches
            for exact in entry.exact_matches:
                if entry.case_sensitive:
                    if exact in content:
                        found.add(exact)
                else:
                    pattern = r"(?i)\b" + exact.replace(".", r"\.") + r"\b"
                    import re
                    for m in re.finditer(pattern, content):
                        found.add(m.group(0))

            # 2. Regex matches
            if entry._compiled_regex:
                for m in entry._compiled_regex.finditer(content):
                    found.add(m.group(0))

        return found

    def enrich(self, token: str) -> Optional[Dict[str, Any]]:
        return self.manager.enrich_token(token)

    def get_ast_attributes(self, token: str) -> Dict[str, str]:
        entry = self.manager.find_entry(token)
        entry_id = entry.id if entry else token
        return {
            "class": "cyber-ioc custom-pill",
            "data-ioc-type": "custom",
            "data-ioc-value": entry_id
        }
