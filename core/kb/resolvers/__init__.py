"""
core/kb/resolvers/__init__.py
Registry of token resolvers.
"""

from typing import Dict, List, Type
from core.kb.resolvers.base import BaseResolver
from core.kb.resolvers.cve_resolver import CveResolver
from core.kb.resolvers.cwe_resolver import CweResolver
from core.kb.resolvers.ghsa_resolver import GhsaResolver
from core.kb.resolvers.mitre_resolver import MitreResolver
from core.kb.resolvers.winevent_resolver import WinEventResolver
from core.kb.resolvers.evtx_resolver import EvtxResolver
from core.kb.resolvers.statute_resolver import StatuteResolver
from core.kb.resolvers.ip_resolver import IpResolver
from core.kb.resolvers.hash_resolver import HashResolver

RESOLVER_REGISTRY: Dict[str, Type[BaseResolver]] = {
    "cve": CveResolver,
    "cwe": CweResolver,
    "ghsa": GhsaResolver,
    "mitre": MitreResolver,
    "winevent": WinEventResolver,
    "evtx": EvtxResolver,
    "statute": StatuteResolver,
    "legal": StatuteResolver,
    "ip": IpResolver,
    "hash": HashResolver,
}

def get_default_resolvers(catalog=None) -> List[BaseResolver]:
    return [
        CveResolver(),
        CweResolver(catalog=catalog),
        GhsaResolver(catalog=catalog),
        MitreResolver(catalog=catalog),
        WinEventResolver(catalog=catalog),
        EvtxResolver(catalog=catalog),
        StatuteResolver(catalog=catalog),
        IpResolver(catalog=catalog),
        HashResolver(catalog=catalog)
    ]
