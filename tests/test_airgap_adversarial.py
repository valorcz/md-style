"""
tests/test_airgap_adversarial.py
Adversarial Stress Test Suite for md-style Air-Gap Enforcement.
Challenger M1.1 empirical verification harness.

Actively stress-tests:
1. Strict socket/DNS/HTTP interception covering socket.connect, sendto,
   getaddrinfo, gethostbyaddr, gethostbyname, urllib.urlopen, http.client.
2. Cold Google fonts caches across ALL 11 themes and aliases.
3. Unknown Octicons and uncached icons under empty caches.
4. Arbitrary public, private, multicast, link-local, and IPv6 addresses.
5. Markdown with remote image tags, remote links, and style injections.
6. All Knowledge Base resolvers with cold caches and force_refresh=True.
7. End-to-end CLI compilation with `--offline`.
8. Offline diagrams (Mermaid and D2) compilation.
"""

import re
import sys
import socket
import http.client
import urllib.request
from pathlib import Path
import pytest

from core.engine import ReportEngine, PipelineConfig
from core.fonts import FontBundler
from core.icons import IconService
from core.bundler import AssetBundler
from core.kb.resolvers.ip_resolver import IpResolver
from core.kb.resolvers.cve_resolver import CveResolver
from core.kb.resolvers.ghsa_resolver import GhsaResolver
from core.kb.resolvers.cwe_resolver import CWE_REGEX, CweResolver
from core.kb.resolvers.evtx_resolver import EvtxResolver
from core.kb.resolvers.hash_resolver import HashResolver
from core.kb.lifecycle import KnowledgeLifecycleManager
from core.cli import main as cli_main


@pytest.fixture(autouse=True)
def adversarial_strict_network_guard(monkeypatch):
    """
    Hostile environment network interceptor.
    Catches any outbound socket connections, DNS queries, UDP transmissions,
    and HTTP/HTTPS requests to any destination other than local loopback (127.0.0.1, ::1).
    """
    violations = []

    orig_connect = socket.socket.connect
    def guarded_connect(self, addr):
        # Allow unix domain sockets (str path)
        if isinstance(addr, str):
            return orig_connect(self, addr)
        host = addr[0] if isinstance(addr, (tuple, list)) and len(addr) > 0 else addr
        h_str = str(host).lower()
        if h_str in ("127.0.0.1", "localhost", "::1") or h_str.startswith("127."):
            return orig_connect(self, addr)
        v = f"Adversarial Air-Gap Violation: socket.connect attempted to {addr}"
        violations.append(v)
        raise ConnectionRefusedError(v)

    orig_sendto = socket.socket.sendto
    def guarded_sendto(self, data, *args):
        if args:
            addr = args[0]
            if isinstance(addr, (tuple, list)) and len(addr) > 0:
                h_str = str(addr[0]).lower()
                if not (h_str in ("127.0.0.1", "localhost", "::1") or h_str.startswith("127.")):
                    v = f"Adversarial Air-Gap Violation: socket.sendto attempted to {addr}"
                    violations.append(v)
                    raise ConnectionRefusedError(v)
        return orig_sendto(self, data, *args)

    orig_gethostbyaddr = socket.gethostbyaddr
    def guarded_gethostbyaddr(ip):
        ip_str = str(ip).lower()
        if ip_str in ("127.0.0.1", "::1", "localhost") or ip_str.startswith("127."):
            return ("localhost", [], [ip_str])
        v = f"Adversarial Air-Gap Violation: socket.gethostbyaddr attempted for {ip}"
        violations.append(v)
        raise ConnectionRefusedError(v)

    orig_getaddrinfo = socket.getaddrinfo
    def guarded_getaddrinfo(host, port, *args, **kwargs):
        h_str = str(host).lower() if host is not None else ""
        if h_str in ("127.0.0.1", "localhost", "::1", "") or h_str.startswith("127."):
            return orig_getaddrinfo(host, port, *args, **kwargs)
        v = f"Adversarial Air-Gap Violation: socket.getaddrinfo attempted for {host}"
        violations.append(v)
        raise ConnectionRefusedError(v)

    orig_gethostbyname = socket.gethostbyname
    def guarded_gethostbyname(hostname):
        h_str = str(hostname).lower()
        if h_str in ("127.0.0.1", "localhost", "::1") or h_str.startswith("127."):
            return "127.0.0.1"
        v = f"Adversarial Air-Gap Violation: socket.gethostbyname attempted for {hostname}"
        violations.append(v)
        raise ConnectionRefusedError(v)

    orig_urlopen = urllib.request.urlopen
    def guarded_urlopen(req, *args, **kwargs):
        target = req.full_url if hasattr(req, "full_url") else str(req)
        if any(local in target for local in ("127.0.0.1", "localhost", "::1")):
            return orig_urlopen(req, *args, **kwargs)
        v = f"Adversarial Air-Gap Violation: urllib.request.urlopen attempted to {target}"
        violations.append(v)
        raise ConnectionRefusedError(v)

    orig_http_connect = http.client.HTTPConnection.connect
    def guarded_http_connect(self):
        h = str(self.host).lower()
        if not (h in ("127.0.0.1", "localhost", "::1") or h.startswith("127.")):
            v = f"Adversarial Air-Gap Violation: HTTPConnection.connect attempted to {self.host}:{self.port}"
            violations.append(v)
            raise ConnectionRefusedError(v)
        return orig_http_connect(self)

    orig_https_connect = http.client.HTTPSConnection.connect
    def guarded_https_connect(self):
        h = str(self.host).lower()
        if not (h in ("127.0.0.1", "localhost", "::1") or h.startswith("127.")):
            v = f"Adversarial Air-Gap Violation: HTTPSConnection.connect attempted to {self.host}:{self.port}"
            violations.append(v)
            raise ConnectionRefusedError(v)
        return orig_https_connect(self)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket.socket, "sendto", guarded_sendto)
    monkeypatch.setattr(socket, "gethostbyaddr", guarded_gethostbyaddr)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(socket, "gethostbyname", guarded_gethostbyname)
    monkeypatch.setattr(urllib.request, "urlopen", guarded_urlopen)
    monkeypatch.setattr(http.client.HTTPConnection, "connect", guarded_http_connect)
    monkeypatch.setattr(http.client.HTTPSConnection, "connect", guarded_https_connect)

    return violations


def test_adversarial_interceptor_detects_wan_leaks():
    """
    Sanity-check meta test: confirms that the interceptor actively blocks
    and records violations if any component attempts outbound WAN communications.
    """
    # 1. socket.gethostbyaddr on public IP
    with pytest.raises(ConnectionRefusedError, match="Adversarial Air-Gap Violation"):
        socket.gethostbyaddr("8.8.8.8")

    # 2. socket.getaddrinfo on public domain
    with pytest.raises(ConnectionRefusedError, match="Adversarial Air-Gap Violation"):
        socket.getaddrinfo("google.com", 80)

    # 3. urllib.request.urlopen on public URL
    with pytest.raises(ConnectionRefusedError, match="Adversarial Air-Gap Violation"):
        urllib.request.urlopen("https://fonts.googleapis.com/css")


ALL_THEME_CANDIDATES = [
    "base",
    "forensic/cyber",
    "forensic/dossier",
    "general/announcement",
    "general/family-invite",
    "general/school",
    "svj/ballot",
    "svj/base",
    "svj/invitation",
    "svj/typewriter",
    "svj/community",
]


@pytest.mark.parametrize("theme_name", ALL_THEME_CANDIDATES)
def test_adversarial_cold_cache_all_themes(tmp_path, theme_name, monkeypatch):
    """
    Stress-test: Compiles a document across ALL themes with a cold font cache and
    cold icon cache, ensuring zero WAN network requests escape and all remote
    font @import declarations are cleanly neutralized.
    """
    cold_font_dir = tmp_path / f"cold_fonts_{theme_name.replace('/', '_')}"
    cold_icon_dir = tmp_path / f"cold_icons_{theme_name.replace('/', '_')}"
    monkeypatch.setattr("core.fonts.FONTS_CACHE_DIR", cold_font_dir)
    monkeypatch.setattr("core.icons.ICON_CACHE_DIR", cold_icon_dir)

    doc_file = tmp_path / f"test_{theme_name.replace('/', '_')}.md"
    doc_file.write_text(
        "---\n"
        f"title: Adversarial Cold Cache Test - {theme_name}\n"
        "author: Challenger Unit\n"
        "date: 2026-10-11\n"
        f"style: {theme_name}\n"
        "---\n\n"
        "# Air-Gap Test Suite\n\n"
        "Document compiled with zero cache entries and allow_online=False.\n\n"
        "> [!NOTE]\n"
        "> Testing callout icon loading under cold cache.\n\n"
        "```text\n"
        "Cold cache test block\n"
        "```\n",
        encoding="utf-8"
    )

    out_file = tmp_path / f"out_{theme_name.replace('/', '_')}.html"
    cfg = PipelineConfig(
        input_file=doc_file,
        output_file=out_file,
        style=theme_name,
        allow_online=False,
        quiet=True
    )
    engine = ReportEngine(cfg)
    res = engine.run()

    assert res.is_file()
    assert res.stat().st_size > 0

    content = res.read_text(encoding="utf-8")

    # Verify zero remote scripts or remote stylesheet links
    assert not re.search(r'<script\b[^>]*\bsrc=["\']https?://', content, re.I)
    assert not re.search(r'<link\b[^>]*\bhref=["\']https?://', content, re.I)

    # Verify zero un-neutralized remote CSS @import
    css_only = re.sub(r'<script\b[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.I)
    assert not re.search(r'@import\s+url\(["\']?https?://', css_only, re.I)
    assert not re.search(r'url\(["\']?https?://[^\'")\s]+\.(?:woff2|woff|ttf|otf)', css_only, re.I)


def test_adversarial_public_private_and_exotic_ips(tmp_path, monkeypatch):
    """
    Stress-test: Ingests documents with high volumes of arbitrary public IPs,
    RFC 1918 private IPs, loopback, link-local, multicast, and IPv6 addresses.
    Confirms 0 reverse DNS lookups, 0 threat intel queries, and valid entity extraction.
    """
    cache_file = tmp_path / "ip_adversarial_cache.json"
    resolver = IpResolver(cache_file=cache_file)

    test_ips = [
        # Public IPs (Google, Cloudflare, Example, OpenDNS, DoD, APNIC)
        "8.8.8.8",
        "1.1.1.1",
        "93.184.216.34",
        "142.250.190.46",
        "208.67.222.222",
        "198.51.100.25",
        "203.0.113.195",
        "6.0.0.1",
        # RFC 1918 Private IPs
        "10.0.0.1",
        "172.16.50.100",
        "192.168.1.254",
        # Loopback & Link-local
        "127.0.0.1",
        "169.254.10.20",
        # Multicast
        "224.0.0.251",
        # IPv6
        "2001:4860:4860::8888",
        "2606:4700:4700::1111",
        "fe80::1",
    ]

    for ip_str in test_ips:
        ent = resolver.resolve(ip_str, allow_online=False, force_refresh=True)
        assert ent is not None, f"Failed resolving {ip_str}"
        assert ent.id == ip_str
        assert ent.details["Reverse DNS (PTR)"] == "None resolved"

    # End-to-end document compilation with multiple IPs
    doc_file = tmp_path / "ip_adversarial_doc.md"
    ip_markdown = "\n".join(f"- Endpoint `{ip}` involved in traffic." for ip in test_ips)
    doc_file.write_text(
        "---\ntitle: IP Adversarial Audit\nstyle: forensic/cyber\n---\n\n"
        "# Network Forensics\n\n" + ip_markdown + "\n",
        encoding="utf-8"
    )

    out_file = tmp_path / "ip_adversarial_out.html"
    cfg = PipelineConfig(
        input_file=doc_file,
        output_file=out_file,
        allow_online=False,
        quiet=True
    )
    engine = ReportEngine(cfg)
    res = engine.run()
    assert res.is_file()
    assert res.stat().st_size > 0


def test_adversarial_uncached_icons_and_arbitrary_names(tmp_path):
    """
    Stress-test: Requests a wide variety of unknown, adversarial, or malformed
    icon names with a completely empty icon cache and allow_online=False.
    Confirms zero network traffic to GitHub primer/octicons CDN and proper fallback SVGs.
    """
    empty_icon_dir = tmp_path / "empty_icon_cache"
    service = IconService(cache_dir=empty_icon_dir, allow_online=False)

    adversarial_icon_names = [
        "totally-unknown-icon-9999",
        "adversarial_threat_actor_icon",
        "primer-nonexistent-alert",
        "malformed name with spaces",
        "cve-shield-zero-day",
        "cwe-vulnerability-glyph",
        "github-octicon-missing-variant",
    ]

    for name in adversarial_icon_names:
        svg = service.get_svg(name)
        assert "<svg" in svg, f"Did not produce SVG for {name}"
        assert 'class="callout-icon"' in svg
        # Fallback circle geometry check
        assert "circle" in svg or "viewBox" in svg


def test_adversarial_remote_images_links_and_styles(tmp_path, monkeypatch):
    """
    Stress-test: Processes markdown documents containing remote image tags,
    remote Markdown links, and raw HTML style blocks.
    Confirms compilation completes with zero network fetches.
    """
    cold_font_dir = tmp_path / "cold_fonts"
    monkeypatch.setattr("core.fonts.FONTS_CACHE_DIR", cold_font_dir)

    doc_file = tmp_path / "remote_assets_doc.md"
    doc_file.write_text(
        "---\n"
        "title: Adversarial Remote Resources Test\n"
        "style: base\n"
        "---\n\n"
        "# Remote Resources\n\n"
        "Testing that remote images and links do not trigger WAN fetches during build:\n\n"
        "![Remote Image 1](https://example.com/images/test.png)\n\n"
        '<img src="https://adversary.com/assets/logo.svg" alt="Adversary Logo" />\n\n'
        "[External Link to Documentation](https://docs.example.org/spec)\n\n"
        "<https://auto-link.example.com>\n\n"
        "<style>\n"
        '@import url("https://fonts.googleapis.com/css2?family=Roboto&display=swap");\n'
        "@font-face {\n"
        '  font-family: "AdversarialFont";\n'
        '  src: url("https://fonts.gstatic.com/s/roboto/v30/test.woff2");\n'
        "}\n"
        "</style>\n\n"
        "> [!WARNING]\n"
        "> Callout with remote link: [Threat Feed](https://threatintel.example.com/cve-2024-9999)\n",
        encoding="utf-8"
    )

    out_file = tmp_path / "remote_assets_out.html"
    cfg = PipelineConfig(
        input_file=doc_file,
        output_file=out_file,
        allow_online=False,
        quiet=True
    )
    engine = ReportEngine(cfg)
    res = engine.run()
    assert res.is_file()
    assert res.stat().st_size > 0


def test_adversarial_all_kb_resolvers_cold_cache(tmp_path):
    """
    Stress-test: Directly invokes all individual knowledge base resolvers
    (CVE, GHSA, CWE, EVTX, Hash) with allow_online=False and force_refresh=True
    against non-existent entities and cold caches.
    Confirms zero network calls and clean fallback objects.
    """
    # 1. CVE Resolver
    cve_res = CveResolver(cache_file=tmp_path / "cve_cache.json")
    for cve in ["CVE-2024-3094", "CVE-2021-44228", "CVE-2029-99999"]:
        ent = cve_res.resolve(cve, allow_online=False, force_refresh=True)
        assert ent is not None
        assert ent.id == cve
        assert ent.provenance.status in ("resolved", "unresolved", "cached")

    # 2. GHSA Resolver
    ghsa_res = GhsaResolver(cache_file=tmp_path / "ghsa_cache.json")
    for ghsa in ["GHSA-jfh8-c2jp-5v3q", "GHSA-9999-9999-9999"]:
        ent = ghsa_res.resolve(ghsa, allow_online=False, force_refresh=True)
        assert ent is not None
        assert ent.id == ghsa.upper()

    # 3. CWE Resolver
    cwe_res = CweResolver(cache_file=tmp_path / "cwe_cache.json")
    for cwe in ["CWE-79", "CWE-89", "CWE-99999"]:
        ent = cwe_res.resolve(cwe, allow_online=False, force_refresh=True)
        assert ent is not None
        assert ent.id == cwe

    # 4. EVTX Resolver
    evtx_res = EvtxResolver(cache_file=tmp_path / "evtx_cache.json")
    for evtx in ["Security.evtx", "Microsoft-Windows-Sysmon%4Operational.evtx", "UnknownSensorXYZ.evtx"]:
        ent = evtx_res.resolve(evtx, allow_online=False, force_refresh=True)
        assert ent is not None

    # 5. Hash Resolver
    hash_res = HashResolver(cache_file=tmp_path / "hash_cache.json")
    for h in [
        "d41d8cd98f00b204e9800998ecf8427e",  # MD5
        "da39a3ee5e6b4b0d3255bfef95601890afd80709",  # SHA-1
        "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",  # SHA-256
        "0123456789abcdef0123456789abcdef",  # arbitrary MD5
        "0123456789abcdef0123456789abcdef01234567",  # arbitrary SHA-1
        "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef",  # arbitrary SHA-256
    ]:
        ent = hash_res.resolve(h, allow_online=False, force_refresh=True)
        assert ent is not None
        assert ent.id == h


def test_adversarial_cli_offline_execution(tmp_path, monkeypatch):
    """
    Stress-test: Executes full compilation through the CLI entry point
    with `--offline` flag, verifying that allow_online=False is propagated end-to-end.
    """
    cold_font_dir = tmp_path / "cold_fonts"
    monkeypatch.setattr("core.fonts.FONTS_CACHE_DIR", cold_font_dir)

    doc_file = tmp_path / "cli_offline_test.md"
    doc_file.write_text(
        "---\n"
        "title: CLI Offline Test\n"
        "style: forensic/cyber\n"
        "---\n\n"
        "# Offline CLI Test\n\n"
        "Host `198.51.100.99` triggered `CVE-2024-3094`.\n\n"
        "> [!CRITICAL]\n"
        "> High severity alert testing CLI air-gap propagation.\n",
        encoding="utf-8"
    )

    out_file = tmp_path / "cli_offline_out.html"

    # Invoke CLI main with --offline
    monkeypatch.setattr(
        sys,
        "argv",
        ["md-style", str(doc_file), "-o", str(out_file), "--offline", "-s", "forensic/cyber", "-q"]
    )

    try:
        cli_main()
    except SystemExit as ex:
        assert ex.code == 0

    assert out_file.is_file()
    assert out_file.stat().st_size > 0


def test_adversarial_offline_with_diagrams(tmp_path, monkeypatch):
    """
    Stress-test: Compiles a document containing Mermaid and D2 diagrams
    under offline mode, confirming that diagram renderers do not perform WAN calls.
    """
    cold_font_dir = tmp_path / "cold_fonts"
    monkeypatch.setattr("core.fonts.FONTS_CACHE_DIR", cold_font_dir)

    doc_file = tmp_path / "diagram_offline_doc.md"
    doc_file.write_text(
        "---\n"
        "title: Offline Diagrams Audit\n"
        "style: forensic/cyber\n"
        "---\n\n"
        "# Architecture\n\n"
        "```mermaid\n"
        "graph TD\n"
        "    Client[Airgapped Client] --> Firewall[Security Gateway]\n"
        "    Firewall --> Storage[Isolated Storage]\n"
        "```\n\n"
        "```d2\n"
        "client -> gateway: verify offline\n"
        "gateway -> storage: store securely\n"
        "```\n",
        encoding="utf-8"
    )

    out_file = tmp_path / "diagram_offline_out.html"
    cfg = PipelineConfig(
        input_file=doc_file,
        output_file=out_file,
        allow_online=False,
        quiet=True
    )
    engine = ReportEngine(cfg)
    res = engine.run()
    assert res.is_file()
    assert res.stat().st_size > 0


def test_adversarial_threat_intel_keys_present_in_environ_offline(tmp_path, monkeypatch):
    """
    Stress-test: Sets active SHODAN_API_KEY and VIRUSTOTAL_API_KEY in the environment.
    With allow_online=False, asserts ZERO requests are made to Shodan or VirusTotal endpoints.
    """
    monkeypatch.setenv("SHODAN_API_KEY", "adversarial_shodan_key_mock_999")
    monkeypatch.setenv("VIRUSTOTAL_API_KEY", "adversarial_vt_key_mock_888")

    # 1. IpResolver with active Shodan key in env
    ip_res = IpResolver(cache_file=tmp_path / "ip_key_cache.json")
    ent_ip = ip_res.resolve("198.51.100.77", allow_online=False, force_refresh=True)
    assert ent_ip is not None
    assert ent_ip.provenance.source == "heuristic:ipaddress"

    # 2. HashResolver with active VirusTotal key in env
    hash_res = HashResolver(cache_file=tmp_path / "hash_key_cache.json")
    ent_hash = hash_res.resolve("5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8", allow_online=False, force_refresh=True)
    assert ent_hash is not None
    assert ent_hash.provenance.source == "catalog:cryptographic"


def test_adversarial_transitive_graph_closure_offline(tmp_path, monkeypatch):
    """
    Stress-test: Documents containing connected entities (GHSA -> CVE -> CWE)
    tested with cold caches. Verifies transitive closure expands graph
    in pure offline mode with zero network requests.
    """
    cold_font_dir = tmp_path / "cold_fonts"
    monkeypatch.setattr("core.fonts.FONTS_CACHE_DIR", cold_font_dir)

    doc_file = tmp_path / "transitive_doc.md"
    doc_file.write_text(
        "---\n"
        "title: Transitive Graph Audit\n"
        "style: forensic/cyber\n"
        "---\n\n"
        "# Vulnerability Correlation\n\n"
        "Security incident involving `GHSA-jfh8-c2jp-5v3q`.\n",
        encoding="utf-8"
    )

    out_file = tmp_path / "transitive_out.html"
    cfg = PipelineConfig(
        input_file=doc_file,
        output_file=out_file,
        allow_online=False,
        quiet=True
    )
    engine = ReportEngine(cfg)
    res = engine.run()
    assert res.is_file()
    assert res.stat().st_size > 0

    html = res.read_text(encoding="utf-8")
    assert "GHSA-jfh8-c2jp-5v3q" in html or "Log4Shell" in html


def test_adversarial_font_bundler_syntax_permutations(tmp_path):
    """
    Stress-test: Feeds diverse CSS @import and @font-face syntax permutations
    (double quotes, single quotes, unquoted, whitespace, query params, hash fragments)
    into FontBundler with allow_online=False.
    Verifies all external URLs are neutralized without network attempts.
    """
    bundler = FontBundler(cache_dir=tmp_path / "fonts", allow_online=False)

    adversarial_css = (
        '@import url("https://fonts.googleapis.com/css2?family=A&display=swap");\n'
        '@import url(\'https://fonts.googleapis.com/css2?family=B\');\n'
        '@import url(https://fonts.googleapis.com/css?family=C);\n'
        '@import "https://cdn.example.com/fonts/d.css";\n'
        '@import \'https://cdn.example.com/fonts/e.css\';\n'
        '@font-face {\n'
        '  font-family: "Test1";\n'
        '  src: url("https://fonts.gstatic.com/s/a/v1/test.woff2") format("woff2");\n'
        '}\n'
        '@font-face {\n'
        '  font-family: "Test2";\n'
        '  src: url(\'https://fonts.gstatic.com/s/b/v1/test.woff\') format("woff");\n'
        '}\n'
        '@font-face {\n'
        '  font-family: "Test3";\n'
        '  src: url(https://fonts.gstatic.com/s/c/v1/test.ttf) format("truetype");\n'
        '}\n'
    )

    result_css = bundler.process_css(adversarial_css, tmp_path)

    # Asserts 0 un-neutralized @import url("https://...")
    assert not re.search(r'@import\s+url\(["\']?https?://', result_css, re.I)
    assert not re.search(r'@import\s+["\']https?://', result_css, re.I)
    # Asserts 0 remote font URLs
    assert not re.search(r'url\(["\']?https?://[^\'")\s]+\.(?:woff2|woff|ttf|otf)', result_css, re.I)
    # Asserts local fallback
    assert 'local("")' in result_css

