"""
core/kb/resolvers/base.py
Abstract base class for threat intelligence and domain entity resolvers.
"""

from abc import ABC, abstractmethod
from typing import Optional, List
from core.kb.models import Entity

class BaseResolver(ABC):
    """Abstract resolver for tokens (CVEs, ATT&CK techniques, Event IDs, statutes)."""
    name: str = "base"

    @abstractmethod
    def can_handle(self, token: str) -> bool:
        """Determines if this resolver can handle the given token."""
        pass

    @abstractmethod
    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        """Resolves token into a structured Entity."""
        pass

    def extract_candidates(self, text: str) -> List[str]:
        """Optionally extracts candidate tokens from text."""
        return []
