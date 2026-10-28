"""
core/kb/resolvers/__init__.py
Registry of token resolvers.
"""

from typing import Dict, List, Type, Any
from core.kb.resolvers.base import BaseResolver
from core.kb.resolvers.cve_resolver import CveResolver
from core.kb.resolvers.cwe_resolver import CweResolver
from core.kb.resolvers.ghsa_resolver import GhsaResolver
from core.kb.resolvers.mitre_resolver import MitreResolver
from core.kb.resolvers.winevent_resolver import WinEventResolver
from core.kb.resolvers.evtx_resolver import EvtxResolver
from core.kb.resolvers.statute_resolver import StatuteResolver
from core.kb.resolvers.ico_resolver import IcoResolver
from core.kb.resolvers.iban_resolver import IbanResolver
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
    "ico": IcoResolver,
    "iban": IbanResolver,
    "bank": IbanResolver,
    "ip": IpResolver,
    "hash": HashResolver,
}


def get_resolver_descriptors() -> List[Dict[str, Any]]:
    """Returns detailed metadata about all registered artifact extractors and providers."""
    return [
        {
            "name": "cve",
            "domain": "threat_intel",
            "title": "Common Vulnerabilities and Exposures (CVE)",
            "patterns": ["CVE-2023-38606", "CVE-2024-21413"],
            "provider": "NIST National Vulnerability Database (NVD v2 REST) / Circl.lu",
            "storage": "data/cve.json + ~/.cache/md-style/intel/cve.json",
            "online_dynamic": True
        },
        {
            "name": "cwe",
            "domain": "threat_intel",
            "title": "Common Weakness Enumeration (CWE)",
            "patterns": ["CWE-79", "CWE-89", "CWE-119"],
            "provider": "MITRE CWE XML Catalog",
            "storage": "data/cwe.json",
            "online_dynamic": False
        },
        {
            "name": "ghsa",
            "domain": "threat_intel",
            "title": "GitHub Security Advisories (GHSA)",
            "patterns": ["GHSA-x84c-p2g9-rqv9"],
            "provider": "GitHub Security Advisory Database GraphQL/REST API",
            "storage": "~/.cache/md-style/intel/ghsa.json",
            "online_dynamic": True
        },
        {
            "name": "mitre",
            "domain": "threat_intel",
            "title": "MITRE ATT&CK Enterprise Techniques",
            "patterns": ["T1059.001", "T1003", "T1078"],
            "provider": "MITRE CTI Enterprise STIX 2.1 Repository",
            "storage": "data/mitre-attack.json",
            "online_dynamic": False
        },
        {
            "name": "ip",
            "domain": "threat_intel",
            "title": "IP Addresses (IPv4 / IPv6 Threat Intel & Geo)",
            "patterns": ["192.168.1.1", "203.0.113.195"],
            "provider": "IP-API / AbuseIPDB / Local geo-cache",
            "storage": "~/.cache/md-style/intel/ip.json",
            "online_dynamic": True
        },
        {
            "name": "hash",
            "domain": "threat_intel",
            "title": "File Hashes (MD5, SHA1, SHA256)",
            "patterns": ["44d88612fea8a8f36de82e1278abb02f", "e3b0c44298fc1c149afbf4c8996fb92427ae41e..."],
            "provider": "MalwareBazaar / VirusTotal / Local cache",
            "storage": "~/.cache/md-style/intel/hash.json",
            "online_dynamic": True
        },
        {
            "name": "winevent",
            "domain": "forensics",
            "title": "Windows Event IDs (Security, System, App)",
            "patterns": ["Event ID: 4624", "EID 4688", "Event 1102"],
            "provider": "Ultimate Windows Security / Hayabusa / Zimmerman Maps",
            "storage": "data/windows-events.json + ~/.cache/md-style/intel/windows-events.json",
            "online_dynamic": False
        },
        {
            "name": "evtx",
            "domain": "forensics",
            "title": "Windows Event Log Channels (.evtx)",
            "patterns": ["Security.evtx", "System.evtx", "Microsoft-Windows-Sysmon/Operational.evtx"],
            "provider": "Curated DFIR Windows Channel Catalog & Audit Guidelines",
            "storage": "In-memory SSOT catalog",
            "online_dynamic": False
        },
        {
            "name": "statute",
            "domain": "legal",
            "title": "Czech Legislation & EU Regulations (NOZ, ZoKB, GDPR)",
            "patterns": ["§ 1175 NOZ", "§ 5 zákona č. 181/2014 Sb.", "§ 8a zákona o službách", "čl. 6 GDPR"],
            "provider": "data/statutes.json + Zákony pro lidi (AION CS REST/HTML) + EUR-Lex",
            "storage": "data/statutes.json + ~/.cache/md-style/intel/statutes.json + ~/.config/md-style/statutes.json",
            "online_dynamic": True
        },
        {
            "name": "ico",
            "domain": "legal",
            "title": "Czech Business Entity Identifier (IČO)",
            "patterns": ["IČO: 76543210", "IČ 26168685", "00006947 (Mod-11 checked)"],
            "provider": "Ministry of Finance ARES REST API v2 + Justice.cz Public Register",
            "storage": "~/.cache/md-style/intel/ares_cache.json",
            "online_dynamic": True
        },
        {
            "name": "iban",
            "domain": "finance",
            "title": "Czech Domestic Accounts & International IBANs",
            "patterns": ["1420-76543210/0100", "CZ4401000014200076543210"],
            "provider": "ČNB Bank Clearing Codes Directory + ČBA SPAYD QR Generator",
            "storage": "In-memory ČNB clearing registry",
            "online_dynamic": False
        }
    ]


def get_default_resolvers(catalog=None) -> List[BaseResolver]:
    return [
        CveResolver(),
        CweResolver(catalog=catalog),
        GhsaResolver(catalog=catalog),
        MitreResolver(catalog=catalog),
        WinEventResolver(catalog=catalog),
        EvtxResolver(catalog=catalog),
        StatuteResolver(catalog=catalog),
        IcoResolver(catalog=catalog),
        IbanResolver(catalog=catalog),
        IpResolver(catalog=catalog),
        HashResolver(catalog=catalog)
    ]
