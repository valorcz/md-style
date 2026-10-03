"""
core/enrichers/base.py
Abstract base enricher and modular registry for indicator pattern recognition and enrichment.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, Set, List

class BaseEnricher(ABC):
    """Abstract base class for all indicator enrichers."""
    name: str = "base"
    pattern_description: str = "General indicator"

    @abstractmethod
    def can_handle(self, token: str) -> bool:
        """Returns True if this enricher recognizes the token format."""
        pass

    @abstractmethod
    def extract_tokens(self, content: str) -> Set[str]:
        """Scans text/markdown to discover matching tokens."""
        pass

    @abstractmethod
    def enrich(self, token: str) -> Optional[Dict[str, Any]]:
        """Queries underlying data provider to resolve metadata."""
        pass

    @abstractmethod
    def get_ast_attributes(self, token: str) -> Dict[str, str]:
        """Returns HTML classes and data attributes for the AST element."""
        pass

class EnricherRegistry:
    def __init__(self):
        self._enrichers: List[BaseEnricher] = []

    def register(self, enricher: BaseEnricher):
        self._enrichers.append(enricher)

    def get_all(self) -> List[BaseEnricher]:
        return list(self._enrichers)

    def find_enricher_for(self, token: str) -> Optional[BaseEnricher]:
        clean = token.strip()
        for enricher in self._enrichers:
            if enricher.can_handle(clean):
                return enricher
        return None

    def enrich_token(self, token: str) -> Optional[Dict[str, Any]]:
        enricher = self.find_enricher_for(token)
        if enricher:
            return enricher.enrich(token)
        return None

    def list_enrichers(self) -> List[Dict[str, str]]:
        return [
            {
                "name": e.name,
                "description": e.pattern_description
            }
            for e in self._enrichers
        ]
