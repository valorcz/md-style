"""
core/kb/loaders/base.py
Abstract base class for internal structured data loaders (Excel, CSV, JSON).
"""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, Any, List
from core.kb.models import Entity

class BaseDataLoader(ABC):
    """Abstract data loader for internal domain objects (assets, users, topology)."""

    @abstractmethod
    def load(self, source_path: Path, config: Dict[str, Any]) -> List[Entity]:
        """Loads and extracts Entity instances from a source file."""
        pass
