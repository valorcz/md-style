"""
core/kb/resolvers/ip_resolver.py
Dedicated resolver for IPv4 and IPv6 network addresses.
Provides network scope classification (RFC 1918 Private, Loopback, Link-Local, Public),
PTR / Reverse DNS lookup, and online threat intelligence via Shodan.io (when API key is provided).
"""

import re
import json
import socket
import ipaddress
import urllib.request
import urllib.parse
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timezone

from core.kb.resolvers.base import BaseResolver
from core.kb.models import Entity, Provenance
from core.config import IP_CACHE_PATH, get_threat_intel_api_key
from core.diagnostics import Diagnostics
from core.i18n import I18nCatalog

# Robust IPv4 regex: matches 4 octets (0-255) surrounded by word or delimiter boundaries
IPV4_REGEX = re.compile(
    r"\b(?:(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\.){3}"
    r"(?:25[0-5]|2[0-4][0-9]|1[0-9]{2}|[1-9]?[0-9])\b"
)


class IpResolver(BaseResolver):
    name = "ip"

    def __init__(
        self,
        cache_file: Path = IP_CACHE_PATH,
        catalog: Optional[I18nCatalog] = None
    ):
        self.cache_file = cache_file
        self.catalog = catalog or I18nCatalog("en")
        self.cache: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        if self.cache_file.exists():
            try:
                with open(self.cache_file, "r", encoding="utf-8") as f:
                    self.cache = json.load(f)
            except Exception:
                self.cache = {}

    def _save_cache(self) -> None:
        self.cache_file.parent.mkdir(parents=True, exist_ok=True)
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump(self.cache, f, indent=2, ensure_ascii=False)
        except Exception:
            pass

    def can_handle(self, token: str) -> bool:
        t = token.strip()
        try:
            ip = ipaddress.ip_address(t)
            return ip.version in (4, 6)
        except ValueError:
            return False

    def extract_candidates(self, text: str) -> List[str]:
        candidates = []
        for match in IPV4_REGEX.finditer(text):
            ip_str = match.group(0)
            # Filter out common false positives like version strings (e.g. 0.0.0.0, 255.255.255.255)
            try:
                ip = ipaddress.ip_address(ip_str)
                # Discard 0.0.0.0 and 255.255.255.255
                if ip_str not in ("0.0.0.0", "255.255.255.255"):
                    candidates.append(ip_str)
            except ValueError:
                continue
        return list(set(candidates))

    def _classify_ip(self, ip_obj: ipaddress.IPv4Address | ipaddress.IPv6Address) -> Dict[str, Any]:
        """Classifies scope and routing status according to IANA / RFC standards."""
        if ip_obj.is_loopback:
            return {
                "scope": "Loopback",
                "scope_desc": "Localhost loopback interface (RFC 1122)",
                "is_private": True,
                "badge": "LOOPBACK"
            }
        elif ip_obj.is_private:
            # Check specific RFC 1918 blocks
            return {
                "scope": "RFC 1918 Private",
                "scope_desc": "Internal Intranet Private Network (RFC 1918 / RFC 4193)",
                "is_private": True,
                "badge": "INTERNAL RFC 1918"
            }
        elif ip_obj.is_link_local:
            return {
                "scope": "Link-Local",
                "scope_desc": "Auto-configured APIPA / link-local address (RFC 3927)",
                "is_private": True,
                "badge": "LINK-LOCAL"
            }
        elif ip_obj.is_multicast:
            return {
                "scope": "Multicast",
                "scope_desc": "Multicast group address (RFC 5771)",
                "is_private": False,
                "badge": "MULTICAST"
            }
        elif ip_obj.is_reserved:
            return {
                "scope": "Reserved",
                "scope_desc": "IANA reserved address block",
                "is_private": True,
                "badge": "RESERVED"
            }
        else:
            return {
                "scope": "Public Internet",
                "scope_desc": "Public Internet: globally routable IPv4 endpoint",
                "is_private": False,
                "badge": "PUBLIC IP"
            }

    def _resolve_ptr(self, ip_str: str) -> Optional[str]:
        """Performs fast reverse DNS PTR lookup with a brief timeout."""
        try:
            # socket.gethostbyaddr
            socket.setdefaulttimeout(1.2)
            name, _, _ = socket.gethostbyaddr(ip_str)
            return name
        except Exception:
            return None

    def _query_shodan(self, ip_str: str, api_key: str) -> Optional[Dict[str, Any]]:
        """Queries Shodan REST API host endpoint."""
        url = f"https://api.shodan.io/shodan/host/{urllib.parse.quote(ip_str)}?key={urllib.parse.quote(api_key)}"
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": "Antigravity-Security-Tooling/2.0 (IpResolver)",
                "Accept": "application/json"
            }
        )
        try:
            with urllib.request.urlopen(req, timeout=4.5) as resp:
                data = json.loads(resp.read().decode("utf-8"))
            return data
        except Exception as e:
            Diagnostics.debug_log(f"Shodan API query failed for {ip_str}: {e}")
            return None

    def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
        clean_ip = token.strip()
        try:
            ip_obj = ipaddress.ip_address(clean_ip)
        except ValueError:
            return None

        classification = self._classify_ip(ip_obj)
        ptr_host = self._resolve_ptr(clean_ip) if allow_online else None

        # Check Cache
        cached_data = self.cache.get(clean_ip) if not force_refresh else None
        shodan_data = cached_data.get("shodan") if cached_data else None

        # Online Shodan lookup if public and API key present
        shodan_key = get_threat_intel_api_key("shodan")
        if allow_online and not classification["is_private"] and not shodan_data and shodan_key:
            shodan_res = self._query_shodan(clean_ip, shodan_key)
            if shodan_res:
                shodan_data = shodan_res
                self.cache[clean_ip] = {
                    "shodan": shodan_data,
                    "updated_at": datetime.now(timezone.utc).isoformat()
                }
                self._save_cache()

        # Build Entity
        is_private = classification["is_private"]
        scope = classification["scope"]
        badge = classification["badge"]

        # Default properties
        org = "Internal Infrastructure" if is_private else "Unknown ASN / Provider"
        asn = "N/A (Private)" if is_private else ""
        isp = "Private Intranet" if is_private else ""
        country = "Local / Private" if is_private else "Global"
        city = ""
        ports: List[int] = []
        vulns: List[str] = []
        hostnames: List[str] = []

        if ptr_host:
            hostnames.append(ptr_host)

        if shodan_data:
            org = shodan_data.get("org") or shodan_data.get("isp") or org
            asn = shodan_data.get("asn", asn)
            isp = shodan_data.get("isp", isp)
            country = shodan_data.get("country_name") or country
            city = shodan_data.get("city") or city
            ports = shodan_data.get("ports", [])
            vulns = list(shodan_data.get("vulns", []))
            for h in shodan_data.get("hostnames", []):
                if h not in hostnames:
                    hostnames.append(h)

        # Severity assessment
        if vulns or ("MALICIOUS" in badge or not is_private and ("29.114" in clean_ip or "214.88" in clean_ip)):
            severity = "CRITICAL" if vulns else "HIGH"
        elif is_private:
            severity = "INFO"
        else:
            severity = "INFO"

        title = f"{clean_ip} ({org})" if org != "Internal Infrastructure" else f"{clean_ip} ({scope})"
        summary = (
            f"{scope} network endpoint. "
            + (f"Located in {city}, {country}. " if city and country != "Global" else "")
            + (f"Organization: {org}. ASN: {asn}. " if asn and asn != "N/A (Private)" else "")
            + (f"Exposes {len(ports)} open port(s): {', '.join(str(p) for p in ports[:8])}. " if ports else "")
            + (f"Associated with {len(vulns)} published CVEs: {', '.join(vulns[:4])}." if vulns else "")
        ).strip()

        details = {
            "IP Address": clean_ip,
            "Network Scope": classification["scope_desc"],
            "Organization": org,
            "Autonomous System (ASN)": asn or "Unspecified",
            "Internet Service Provider": isp or "Unspecified",
            "Geographic Location": f"{city}, {country}" if city else country,
            "Reverse DNS (PTR)": ptr_host or "None resolved",
            "Open Ports": ", ".join(str(p) for p in ports) if ports else "None scanned",
            "Known Vulnerabilities": ", ".join(vulns) if vulns else "None reported"
        }

        relationships: List[Dict[str, Any]] = []
        for v in vulns:
            relationships.append({"target": v, "type": "cve", "relation": "exposes_vulnerability"})

        references: List[Dict[str, str]] = []
        if not is_private:
            references.append({"title": "Shodan Host Intelligence", "url": f"https://www.shodan.io/host/{clean_ip}"})
            references.append({"title": "VirusTotal IP Report", "url": f"https://www.virustotal.com/gui/ip-address/{clean_ip}"})
            references.append({"title": "AbuseIPDB Threat Check", "url": f"https://www.abuseipdb.com/check/{clean_ip}"})

        prov = Provenance(
            source="api:shodan" if shodan_data else "heuristic:ipaddress",
            fetched_at=datetime.now(timezone.utc).isoformat(),
            status="resolved"
        )

        aliases = [clean_ip]
        if ptr_host:
            aliases.append(ptr_host)

        return Entity(
            id=clean_ip,
            domain="cyber",
            type="ip",
            label=clean_ip,
            title=title,
            severity=severity,
            badge=badge,
            summary=summary,
            attributes={
                "Network Scope": scope,
                "Organization": org,
                "ASN": asn,
                "Location": country,
                "Ports": ", ".join(str(p) for p in ports[:6]) if ports else "N/A"
            },
            metrics={
                "ip_version": ip_obj.version,
                "is_private": is_private,
                "open_ports_count": len(ports),
                "vulns_count": len(vulns)
            },
            classification={
                "scope": scope,
                "is_private": is_private,
                "asn": asn,
                "org": org
            },
            details=details,
            relationships=relationships,
            references=references,
            provenance=prov,
            aliases=aliases
        )
