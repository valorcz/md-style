"""
core/enrichers/network.py
Enricher for IPv4/IPv6 network indicators and RFC 1918 OPSEC classification.
"""

import ipaddress
import re
from typing import Dict, Any, Optional, Set
from core.enrichers.base import BaseEnricher

IPV4_PATTERN = re.compile(r"^\d{1,3}(?:\.\d{1,3}){3}$")

class NetworkEnricher(BaseEnricher):
    name = "network"
    pattern_description = "IP Addresses (IPv4, IPv6) with RFC 1918 OPSEC classification"

    def can_handle(self, token: str) -> bool:
        clean = token.strip()
        try:
            ipaddress.ip_address(clean)
            return True
        except ValueError:
            return False

    def extract_tokens(self, content: str) -> Set[str]:
        tokens = set()
        for match in re.finditer(r"\b(\d{1,3}(?:\.\d{1,3}){3})\b", content):
            candidate = match.group(1)
            try:
                ipaddress.ip_address(candidate)
                tokens.add(candidate)
            except ValueError:
                pass
        return tokens

    def enrich(self, token: str) -> Optional[Dict[str, Any]]:
        clean = token.strip()
        try:
            ip_obj = ipaddress.ip_address(clean)
        except ValueError:
            return None

        is_private = ip_obj.is_private or ip_obj.is_loopback

        if is_private:
            return {
                "type": "ip",
                "id": clean,
                "title": f"Private Intranet Endpoint ({clean})",
                "summary": "Internal private subnet IP (RFC 1918). External threat intelligence queries are suppressed to protect client confidentiality and investigative OPSEC.",
                "scope": "INTERNAL",
                "subnet": "RFC 1918 (Private LAN)",
                "opsec": "External threat queries suppressed (Confidential client subnet)",
                "version": f"IPv{ip_obj.version}",
                "severity": "PROTECTED",
                "url": "#"
            }
        else:
            return {
                "type": "ip",
                "id": clean,
                "title": f"External Public IP ({clean})",
                "summary": "Publicly routable Internet endpoint. Threat intelligence queries available below to verify IP reputation and abuse history.",
                "scope": "EXTERNAL",
                "subnet": "Public Internet (WAN)",
                "opsec": "External reputation lookups permitted",
                "version": f"IPv{ip_obj.version}",
                "severity": "PUBLIC WAN",
                "url": f"https://www.abuseipdb.com/check/{clean}"
            }

    def get_ast_attributes(self, token: str) -> Dict[str, str]:
        return {
            "class": "ioc cyber-ioc",
            "data-ioc-type": "ip",
            "data-ioc-value": token.strip()
        }
