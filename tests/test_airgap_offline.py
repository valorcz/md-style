"""
tests/test_airgap_offline.py
Automated air-gap strictness and offline compilation test suite.
Asserts ZERO external WAN network requests (DNS, TCP, HTTP) across all themes,
resolvers, asset bundlers, and compilation stages when allow_online=False / --offline.
"""

import re
import socket
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
from core.kb.resolvers.cwe_resolver import CweResolver
from core.kb.resolvers.evtx_resolver import EvtxResolver
from core.cli import build_parser


@pytest.fixture(autouse=True)
def airgap_network_guard(monkeypatch):
    """
    Strict socket and HTTP network interceptor fixture.
    Whitelists only local loopback (127.0.0.1, ::1, localhost, unix domain sockets)
    for inter-process Chromium CDP and local file communications.
    Raises ConnectionRefusedError on ANY external WAN network attempt.
    """
    violations = []

    orig_connect = socket.socket.connect
    def guarded_connect(self, addr):
        # Allow unix domain sockets (represented as string path)
        if isinstance(addr, str):
            return orig_connect(self, addr)
        host = addr[0] if isinstance(addr, (tuple, list)) and len(addr) > 0 else addr
        host_str = str(host)
        if host in ("127.0.0.1", "localhost", "::1") or host_str.startswith("127."):
            return orig_connect(self, addr)
        violation = f"Air-gap violation: socket connect attempted to {addr}"
        violations.append(violation)
        raise ConnectionRefusedError(violation)

    orig_gethostbyaddr = socket.gethostbyaddr
    def guarded_gethostbyaddr(ip):
        ip_str = str(ip)
        if ip_str in ("127.0.0.1", "::1", "localhost") or ip_str.startswith("127."):
            return ("localhost", [], [ip_str])
        violation = f"Air-gap violation: reverse DNS PTR lookup attempted for {ip}"
        violations.append(violation)
        raise ConnectionRefusedError(violation)

    orig_getaddrinfo = socket.getaddrinfo
    def guarded_getaddrinfo(host, port, *args, **kwargs):
        host_str = str(host) if host is not None else ""
        if host_str in ("127.0.0.1", "localhost", "::1", "") or host_str.startswith("127."):
            return orig_getaddrinfo(host, port, *args, **kwargs)
        violation = f"Air-gap violation: DNS forward lookup attempted for {host}"
        violations.append(violation)
        raise ConnectionRefusedError(violation)

    orig_gethostbyname = socket.gethostbyname
    def guarded_gethostbyname(hostname):
        h_str = str(hostname)
        if h_str in ("127.0.0.1", "localhost", "::1") or h_str.startswith("127."):
            return "127.0.0.1"
        violation = f"Air-gap violation: DNS gethostbyname attempted for {hostname}"
        violations.append(violation)
        raise ConnectionRefusedError(violation)

    orig_urlopen = urllib.request.urlopen
    def guarded_urlopen(req, *args, **kwargs):
        target = req.full_url if hasattr(req, "full_url") else str(req)
        if "127.0.0.1" in target or "localhost" in target or "::1" in target:
            return orig_urlopen(req, *args, **kwargs)
        violation = f"Air-gap violation: urllib.request.urlopen attempted to {target}"
        violations.append(violation)
        raise ConnectionRefusedError(violation)

    monkeypatch.setattr(socket.socket, "connect", guarded_connect)
    monkeypatch.setattr(socket, "gethostbyaddr", guarded_gethostbyaddr)
    monkeypatch.setattr(socket, "getaddrinfo", guarded_getaddrinfo)
    monkeypatch.setattr(socket, "gethostbyname", guarded_gethostbyname)
    monkeypatch.setattr(urllib.request, "urlopen", guarded_urlopen)

    return violations


def test_offline_ip_resolver_zero_network(tmp_path):
    """
    Verifies that IpResolver resolves public and private IPs in offline mode
    (allow_online=False) with zero reverse DNS lookups or external API calls.
    """
    cache_file = tmp_path / "ip_test_cache.json"
    resolver = IpResolver(cache_file=cache_file)

    # 1. Test public IP (previously leaked via socket.gethostbyaddr)
    public_ip = "198.51.100.25"
    ent = resolver.resolve(public_ip, allow_online=False)

    assert ent is not None
    assert ent.id == public_ip
    assert ent.details["Reverse DNS (PTR)"] == "None resolved"
    assert ent.provenance.status == "resolved"
    assert ent.provenance.source == "heuristic:ipaddress"

    # 2. Test well-known public DNS IP
    ent_dns = resolver.resolve("8.8.8.8", allow_online=False)
    assert ent_dns is not None
    assert ent_dns.details["Reverse DNS (PTR)"] == "None resolved"

    # 3. Test RFC 1918 private IP
    ent_priv = resolver.resolve("192.168.1.1", allow_online=False)
    assert ent_priv is not None
    assert ent_priv.classification["is_private"] is True


def test_offline_font_bundler_cold_cache(tmp_path):
    """
    Verifies that FontBundler with allow_online=False and a cold/empty cache
    completes without any network requests and cleanly sanitizes external URLs.
    """
    cold_cache = tmp_path / "cold_fonts"
    bundler = FontBundler(cache_dir=cold_cache, allow_online=False)

    test_css = (
        '@import url("https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap");\n'
        '@font-face {\n'
        '  font-family: "RemoteFont";\n'
        '  src: url("https://fonts.gstatic.com/s/inter/v13/test.woff2") format("woff2");\n'
        '}\n'
        'body { font-family: "Inter", sans-serif; }\n'
    )

    result_css = bundler.process_css(test_css, tmp_path)

    # Asserts zero network requests were made (guaranteed by autouse guard)
    # Asserts remote @import was safely suppressed/commented
    assert "@import url(\"https://fonts.googleapis.com" not in result_css
    assert "fonts.googleapis.com" in result_css or "Offline" in result_css

    # Asserts remote font binary url was converted to local fallback
    assert "https://fonts.gstatic.com" not in result_css
    assert 'local("")' in result_css or "data:font" in result_css


def test_offline_font_bundler_warm_cache(tmp_path):
    """
    Verifies that FontBundler in offline mode uses local cache if available
    without making any external network requests.
    """
    cache_dir = tmp_path / "warm_fonts"
    css_cache = cache_dir / "css"
    file_cache = cache_dir / "files"
    css_cache.mkdir(parents=True, exist_ok=True)
    file_cache.mkdir(parents=True, exist_ok=True)

    test_url = "https://fonts.googleapis.com/css?family=CachedFont"
    bundler = FontBundler(cache_dir=cache_dir, allow_online=False)
    url_hash = bundler._hash_url(test_url)

    # Seed mock cached CSS
    (css_cache / f"{url_hash}.css").write_text(
        '/* Cached Font CSS */\n@font-face { font-family: "CachedFont"; src: local("CachedFont"); }',
        encoding="utf-8"
    )

    result = bundler.fetch_css_import(test_url)
    assert result is not None
    assert "Cached Font CSS" in result


def test_offline_icon_service_fallback(tmp_path):
    """
    Verifies that IconService with allow_online=False returns the local fallback SVG
    for uncached/unknown icons without attempting GitHub CDN requests.
    """
    cache_dir = tmp_path / "icon_cache"
    svc = IconService(cache_dir=cache_dir, allow_online=False)

    # Known local asset loads cleanly
    local_svg = svc.get_svg("info")
    assert "<svg" in local_svg

    # Unknown icon skips network and returns minimal vector fallback
    unknown_svg = svc.get_svg("nonexistent-octicon-xyz-999")
    assert "<svg" in unknown_svg
    assert "circle" in unknown_svg or "viewBox" in unknown_svg


def test_offline_knowledge_resolvers_stubs(tmp_path):
    """
    Verifies that vulnerability and telemetry resolvers return clean offline stubs
    without external network requests when allow_online=False.
    """
    # 1. CVE Resolver
    cve_res = CveResolver(cache_file=tmp_path / "cve_test.json")
    cve_ent = cve_res.resolve("CVE-2029-99999", allow_online=False)
    assert cve_ent is not None
    assert cve_ent.id == "CVE-2029-99999"
    assert cve_ent.provenance.status == "unresolved"

    # 2. GHSA Resolver
    ghsa_res = GhsaResolver(cache_file=tmp_path / "ghsa_test.json")
    ghsa_ent = ghsa_res.resolve("GHSA-9999-9999-9999", allow_online=False)
    assert ghsa_ent is not None
    assert ghsa_ent.id == "GHSA-9999-9999-9999"

    # 3. CWE Resolver
    cwe_res = CweResolver(cache_file=tmp_path / "cwe_test.json")
    cwe_ent = cwe_res.resolve("CWE-99999", allow_online=False)
    assert cwe_ent is not None
    assert cwe_ent.id == "CWE-99999"

    # 4. EVTX Resolver
    evtx_res = EvtxResolver(cache_file=tmp_path / "evtx_test.json")
    evtx_ent = evtx_res.resolve("CustomTelemetryUnknown.evtx", allow_online=False)
    assert evtx_ent is not None
    assert "CustomTelemetryUnknown" in evtx_ent.id


@pytest.mark.parametrize("theme_name", [
    "forensic/cyber",
    "forensic/incident",
    "svj/typewriter",
    "svj/invitation",
    "general/family-invite",
    "base"
])
def test_offline_report_engine_compilation_all_themes(tmp_path, theme_name, monkeypatch):
    """
    End-to-end compilation test: Compiles a complex document containing uncached IPs,
    CVEs, callouts, and code blocks across all theme families with allow_online=False
    and an isolated empty cache. Asserts zero WAN requests and valid output HTML.
    """
    # Isolate font cache to force cold-cache branch
    cold_font_cache = tmp_path / f"fonts_{theme_name.replace('/', '_')}"
    monkeypatch.setattr("core.fonts.FONTS_CACHE_DIR", cold_font_cache)

    doc_path = tmp_path / f"report_{theme_name.replace('/', '_')}.md"
    doc_path.write_text(
        "---\n"
        f"title: Offline Airgap Audit - {theme_name}\n"
        "author: Forensic Unit\n"
        "date: 2026-10-11\n"
        f"style: {theme_name}\n"
        "---\n\n"
        "# Incident Triage\n\n"
        "Suspicious telemetry detected from remote endpoint `198.51.100.25` and `8.8.8.8`.\n\n"
        "> [!NOTE]\n"
        "> Correlated with `CVE-2024-9999` and `CWE-79`.\n\n"
        "```python\n"
        "# Offline evidence parser\n"
        "def verify_airgap():\n"
        "    return True\n"
        "```\n\n"
        "| Endpoint | Status |\n"
        "| :--- | :--- |\n"
        "| 198.51.100.25 | Isolated |\n",
        encoding="utf-8"
    )

    out_html = tmp_path / f"output_{theme_name.replace('/', '_')}.html"

    cfg = PipelineConfig(
        input_file=doc_path,
        output_file=out_html,
        style=theme_name,
        highlight_style=None,
        allow_online=False,
        quiet=True
    )

    engine = ReportEngine(cfg)
    result_path = engine.run()

    assert result_path.is_file()
    assert result_path.stat().st_size > 0

    html_content = result_path.read_text(encoding="utf-8")

    # Air-gap deliverable compliance checks
    # 1. Zero external script tags
    remote_scripts = re.findall(r'<script\b[^>]*\bsrc=["\']https?://', html_content, re.IGNORECASE)
    assert len(remote_scripts) == 0, f"Found remote scripts: {remote_scripts}"

    # 2. Zero external stylesheet links
    remote_links = re.findall(r'<link\b[^>]*\bhref=["\']https?://', html_content, re.IGNORECASE)
    assert len(remote_links) == 0, f"Found remote links: {remote_links}"

    # Strip script blocks to test CSS stylesheets specifically
    css_content = re.sub(r'<script\b[^>]*>.*?</script>', '', html_content, flags=re.DOTALL | re.IGNORECASE)

    # 3. Zero remote CSS @import url(...)
    remote_imports = re.findall(r'@import\s+url\(["\']?https?://', css_content, re.IGNORECASE)
    assert len(remote_imports) == 0, f"Found remote CSS @import: {remote_imports}"

    # 4. Zero un-embedded remote font binary references
    remote_font_urls = re.findall(r'url\(["\']?https?://[^\'")\s]+\.(?:woff2|woff|ttf|otf)', css_content, re.IGNORECASE)
    assert len(remote_font_urls) == 0, f"Found remote font URLs: {remote_font_urls}"

    # 5. Core self-contained payloads present
    assert '<main class="report-content">' in html_content
    assert '<script id="md-style-kb-data"' in html_content
    assert '<script id="md-style-i18n"' in html_content
    assert '<div id="md-style-viewer-root">' in html_content


def test_cli_offline_flag_configuration(tmp_path):
    """
    Verifies that the CLI parser sets allow_online=False when --offline is supplied,
    and allow_online=True when --offline is omitted.
    """
    parser = build_parser()
    dummy_doc = str(tmp_path / "doc.md")

    # With --offline
    args_offline = parser.parse_args([dummy_doc, "--offline"])
    assert args_offline.allow_online is False

    # Default without --offline
    args_default = parser.parse_args([dummy_doc])
    assert args_default.allow_online is True
