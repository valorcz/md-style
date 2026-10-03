"""
core/enrichers package
Modular security indicator enrichers and token matcher registry.
"""

from .base import BaseEnricher, EnricherRegistry
from .mitre import MitreEnricher
from .cve import CveEnricher
from .ghsa import GhsaEnricher
from .windows_events import WindowsEventsEnricher
from .network import NetworkEnricher
from .hashes import HashEnricher
from .custom import CustomKnowledgeEnricher

def get_default_registry() -> EnricherRegistry:
    """Builds and returns the default registry populated with all standard enrichers."""
    registry = EnricherRegistry()
    registry.register(MitreEnricher())
    registry.register(CveEnricher())
    registry.register(GhsaEnricher())
    registry.register(WindowsEventsEnricher())
    registry.register(NetworkEnricher())
    registry.register(HashEnricher())
    return registry

default_registry = get_default_registry()
registry = default_registry

__all__ = [
    "BaseEnricher",
    "EnricherRegistry",
    "MitreEnricher",
    "CveEnricher",
    "GhsaEnricher",
    "WindowsEventsEnricher",
    "NetworkEnricher",
    "HashEnricher",
    "CustomKnowledgeEnricher",
    "get_default_registry",
    "default_registry",
    "registry"
]
