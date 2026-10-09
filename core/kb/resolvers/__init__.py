"""
core/kb/resolvers/__init__.py
Registry of token resolvers.
"""

from typing import Dict, List, Type
from core.kb.resolvers.base import BaseResolver
from core.kb.resolvers.cve_resolver import CveResolver
from core.kb.resolvers.mitre_resolver import MitreResolver
from core.kb.resolvers.winevent_resolver import WinEventResolver
from core.kb.resolvers.statute_resolver import StatuteResolver

RESOLVER_REGISTRY: Dict[str, Type[BaseResolver]] = {
    "cve": CveResolver,
    "mitre": MitreResolver,
    "winevent": WinEventResolver,
    "statute": StatuteResolver,
    "legal": StatuteResolver,
}

def get_default_resolvers(catalog=None) -> List[BaseResolver]:
    return [
        CveResolver(),
        MitreResolver(),
        WinEventResolver(catalog=catalog),
        StatuteResolver(catalog=catalog)
    ]
