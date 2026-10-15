"""
tests/test_kb_resolvers.py
Unit tests verifying EVTX, Windows Events, MITRE ATT&CK, and GHSA knowledge resolvers,
rich object models, cross-references, and relationships without hardcoded Python dicts.
"""

from pathlib import Path
from core.kb.resolvers.evtx_resolver import EvtxResolver
from core.kb.resolvers.winevent_resolver import WinEventResolver
from core.kb.resolvers.mitre_resolver import MitreResolver
from core.kb.resolvers.ghsa_resolver import GhsaResolver
from core.kb.resolvers.cve_resolver import CveResolver
from core.kb.models import Entity


def test_evtx_resolver_curated():
    """Verifies EvtxResolver resolves curated Windows event log channels with rich details."""
    resolver = EvtxResolver()
    assert resolver.can_handle("Security.evtx") is True
    assert resolver.can_handle("System.evtx") is True
    assert resolver.can_handle("Sysmon") is True

    ent = resolver.resolve("System.evtx", allow_online=False)
    assert ent is not None
    assert ent.type == "evtx"
    assert "System Event Log" in ent.title
    assert "7045" in ent.details.get("Key Event IDs", "")
    assert len(ent.relationships) > 0
    # Cross-links to hosted event IDs
    targets = [r["target"] for r in ent.relationships]
    assert "Event-7045" in targets


def test_evtx_resolver_shorthand_alias():
    """Verifies EvtxResolver resolves shorthand aliases like 'Sysmon' and 'bits'."""
    resolver = EvtxResolver()
    ent = resolver.resolve("Sysmon", allow_online=False)
    assert ent is not None
    assert "Sysmon" in ent.title
    assert ent.type == "evtx"
    assert "Event-1" in [r["target"] for r in ent.relationships]


def test_evtx_resolver_expanded_channels():
    """Verifies expanded DFIR channels (BITS, CodeIntegrity, Defender) resolve from JSON."""
    resolver = EvtxResolver()
    assert resolver.can_handle("bits") is True
    assert resolver.can_handle("Microsoft-Windows-Bits-Client/Operational.evtx") is True
    assert resolver.can_handle("codeintegrity") is True

    bits_ent = resolver.resolve("bits", allow_online=False)
    assert bits_ent is not None
    assert "BITS" in bits_ent.title or "Background Intelligent" in bits_ent.title
    assert "Event-3" in [r["target"] for r in bits_ent.relationships]

    ci_ent = resolver.resolve("Microsoft-Windows-CodeIntegrity/Operational.evtx", allow_online=False)
    assert ci_ent is not None
    assert "CodeIntegrity" in ci_ent.id or "Code Integrity" in ci_ent.title


def test_evtx_resolver_path_normalization():
    """Verifies that full Windows paths, environment prefixes, and filenames resolve to the same canonical entity."""
    resolver = EvtxResolver()

    # Sysmon variants
    sysmon_paths = [
        "Sysmon.evtx",
        "System32\\Winevt\\Logs\\Sysmon.evtx",
        "%SystemRoot%\\System32\\Winevt\\Logs\\Sysmon.evtx",
        "System32/Winevt/Logs/Sysmon.evtx",
        "%SystemRoot%/System32/Winevt/Logs/Sysmon.evtx"
    ]
    for p in sysmon_paths:
        assert resolver.can_handle(p) is True
        ent = resolver.resolve(p, allow_online=False)
        assert ent is not None
        assert ent.id == "Sysmon.evtx"
        assert ent.title == "Microsoft Sysmon Operational Telemetry Log"
        assert "Sysmon.evtx" in ent.aliases
        assert "Sysmon" in ent.aliases

    # Security variants
    sec_paths = [
        "Security.evtx",
        "System32\\Winevt\\Logs\\Security.evtx",
        "%SystemRoot%\\System32\\Winevt\\Logs\\Security.evtx"
    ]
    for p in sec_paths:
        assert resolver.can_handle(p) is True
        ent = resolver.resolve(p, allow_online=False)
        assert ent is not None
        assert ent.id == "Security.evtx"
        assert "Security Event Log" in ent.title


def test_winevent_resolver_authoritative_db():
    """Verifies WinEventResolver resolves authoritative events from data/windows-events.json."""
    resolver = WinEventResolver()
    assert resolver.can_handle("Event 4624") is True
    assert resolver.can_handle("EID 7045") is True
    assert resolver.can_handle("4624") is True

    ent_4624 = resolver.resolve("Event 4624", allow_online=False)
    assert ent_4624 is not None
    assert ent_4624.type == "winevent"
    assert "logged on" in ent_4624.title.lower()
    targets = [r["target"] for r in ent_4624.relationships]
    assert "Security.evtx" in targets
    # Cross-link to MITRE T1078 (Valid Accounts)
    assert "T1078" in targets

    ent_7045 = resolver.resolve("EID 7045", allow_online=False)
    assert ent_7045 is not None
    assert "service" in ent_7045.title.lower()
    assert "System.evtx" in [r["target"] for r in ent_7045.relationships]


def test_mitre_resolver_authoritative_db():
    """Verifies MitreResolver resolves techniques and subtechniques from data/mitre-attack.json."""
    resolver = MitreResolver()
    assert resolver.can_handle("T1059") is True
    assert resolver.can_handle("T1059.001") is True
    assert resolver.can_handle("T1003") is True

    # Root technique
    ent_t1059 = resolver.resolve("T1059", allow_online=False)
    assert ent_t1059 is not None
    assert ent_t1059.id == "T1059"
    assert "Command and Scripting Interpreter" in ent_t1059.title
    assert "Execution" in ent_t1059.details.get("Primary Tactic", "")

    # Sub-technique linking to parent
    ent_sub = resolver.resolve("T1059.001", allow_online=False)
    assert ent_sub is not None
    assert ent_sub.id == "T1059.001"
    assert "PowerShell" in ent_sub.title
    sub_targets = [r["target"] for r in ent_sub.relationships if r["relation"] == "subtechnique_of"]
    assert "T1059" in sub_targets


def test_ghsa_resolver_can_handle():
    """Verifies GhsaResolver pattern matching and extraction."""
    resolver = GhsaResolver()
    valid_id = "GHSA-jfh8-c2jp-5v3q"
    assert resolver.can_handle(valid_id) is True
    assert resolver.can_handle("CVE-2024-21762") is False

    extracted = resolver.extract_candidates(f"Found advisory {valid_id} in report.")
    assert valid_id in extracted


def test_ghsa_resolver_offline_fallback():
    """Verifies GhsaResolver fallback structure in offline mode."""
    resolver = GhsaResolver()
    valid_id = "GHSA-jfh8-c2jp-5v3q"
    ent = resolver.resolve(valid_id, allow_online=False)
    assert ent is not None
    assert ent.type == "ghsa"
    assert ent.id == valid_id.upper()
    assert ent.domain == "cyber"


def test_entity_rich_fields_serialization():
    """Verifies Entity model properly serializes metrics, classification, details, and relationships."""
    ent = Entity(
        id="CVE-2026-3184",
        domain="cyber",
        type="cve",
        label="CVE-2026-3184",
        title="Perimeter VPN RCE",
        severity="CRITICAL",
        metrics={"cvss_score": 9.8, "cvss_vector": "CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H"},
        classification={"cwes": ["CWE-120"], "tactics": ["Initial Access"]},
        details={"Patch Version": "v14.2.9-hotfix", "Affected": "Enterprise Ingress"},
        relationships=[{"target": "System.evtx", "type": "evtx", "relation": "logged_in"}],
        aliases=["CVE-2026-3184"]
    )

    d = ent.to_dict()
    assert d["metrics"]["cvss_score"] == 9.8
    assert d["classification"]["cwes"] == ["CWE-120"]
    assert d["details"]["Patch Version"] == "v14.2.9-hotfix"
    assert d["relationships"][0]["target"] == "System.evtx"

    restored = Entity.from_dict(d)
    assert restored.metrics == ent.metrics
    assert restored.classification == ent.classification
    assert restored.details == ent.details
    assert restored.relationships == ent.relationships


def test_entity_widget_descriptor_serialization():
    """Verifies that Entity.widgets serialization and roundtrip preserves widget specifications."""
    from core.kb.models import Entity, WidgetDescriptor

    gauge_widget = WidgetDescriptor(
        widget_type="gauge",
        title="CVSS Gauge",
        tone="threat",
        data={"score": 9.8, "severity": "CRITICAL", "vector": "CVSS:3.1/AV:N/AC:L"}
    )
    tactic_widget = WidgetDescriptor(
        widget_type="tactical_box",
        title="Adversary Playbook",
        tone="threat",
        items=["Command injection", "Privilege escalation"],
        data={"code": "powershell.exe -enc ...", "codeLabel": "Observed Execution:"}
    )

    ent = Entity(
        id="CVE-2024-38077",
        domain="cyber",
        type="cve",
        label="CVE-2024-38077",
        title="Windows RDLAC RCE",
        widgets=[gauge_widget, tactic_widget]
    )

    payload = ent.to_dict()
    assert "widgets" in payload
    assert len(payload["widgets"]) == 2
    assert payload["widgets"][0]["widget_type"] == "gauge"
    assert payload["widgets"][0]["data"]["score"] == 9.8
    assert payload["widgets"][1]["items"] == ["Command injection", "Privilege escalation"]

    restored = Entity.from_dict(payload)
    assert len(restored.widgets) == 2
    assert isinstance(restored.widgets[0], WidgetDescriptor)
    assert restored.widgets[0].widget_type == "gauge"
    assert restored.widgets[1].items == ["Command injection", "Privilege escalation"]


def test_cve_resolver_rich_metrics():
    """Verifies CveResolver produces rich metrics, affected software, and vector string."""
    resolver = CveResolver()
    assert resolver.can_handle("CVE-2024-21762") is True

    ent = resolver.resolve("CVE-2024-21762", allow_online=False)
    assert ent is not None
    assert ent.type == "cve"
    assert "Fortinet" in ent.title or "FortiOS" in ent.title
    assert ent.severity == "CRITICAL"
    assert ent.metrics.get("cvss_score") == 9.6
    assert "CVSS:3.1" in ent.metrics.get("cvss_vector", "")
    assert ent.metrics.get("attack_vector") == "NETWORK"
    assert ent.metrics.get("attack_complexity") == "LOW"
    assert "CWE-787" in ent.classification.get("cwes", [])
    assert len(ent.references) >= 2


def test_cve_resolver_log4j_seed():
    """Verifies Log4Shell (CVE-2021-44228) resolves with deserialization CWE and score 10.0."""
    resolver = CveResolver()
    ent = resolver.resolve("CVE-2021-44228", allow_online=False)
    assert ent is not None
    assert "Log4j" in ent.title or "Log4Shell" in ent.title
    assert ent.metrics.get("cvss_score") == 10.0
    assert "CWE-502" in ent.classification.get("cwes", [])
    assert ent.metrics.get("attack_vector") == "NETWORK"


def test_cve_resolver_cpe_extraction():
    """Verifies CveResolver extracts and synthesizes authoritative CPE 2.3 identifiers."""
    resolver = CveResolver()
    ent_forti = resolver.resolve("CVE-2024-21762", allow_online=False)
    assert ent_forti is not None
    cpes_forti = ent_forti.classification.get("cpes", [])
    assert len(cpes_forti) > 0
    assert any("fortinet:fortios" in cpe for cpe in cpes_forti)

    ent_log4j = resolver.resolve("CVE-2021-44228", allow_online=False)
    assert ent_log4j is not None
    cpes_log4j = ent_log4j.classification.get("cpes", [])
    assert len(cpes_log4j) > 0
    assert any("log4j" in cpe and "apache" in cpe for cpe in cpes_log4j)


def test_evtx_bare_stopwords_disambiguation():
    """Verifies that bare generic words (System, Defender, Security) are NOT handled as EVTX files."""
    resolver = EvtxResolver()

    # Bare generic words must return False
    assert resolver.can_handle("System") is False
    assert resolver.can_handle("Defender") is False
    assert resolver.can_handle("Security") is False
    assert resolver.can_handle("Application") is False
    assert resolver.can_handle("Firewall") is False

    # Qualified files must return True
    assert resolver.can_handle("System.evtx") is True
    assert resolver.can_handle("Defender.evtx") is True
    assert resolver.can_handle("Security.evtx") is True

    # Aliases of System.evtx must NOT contain bare "System"
    sys_ent = resolver.resolve("System.evtx", allow_online=False)
    assert sys_ent is not None
    assert "System" not in sys_ent.aliases
    assert "System.evtx" in sys_ent.aliases


def test_ip_resolver_classification():
    """Verifies IpResolver classifies RFC 1918 private vs public endpoints without crashing."""
    from core.kb.resolvers.ip_resolver import IpResolver
    resolver = IpResolver()

    # Candidate extraction
    text = "C2 server at 194.26.29.114 communicated with DC-01 at 10.0.4.15 and loopback 127.0.0.1."
    candidates = resolver.extract_candidates(text)
    assert "194.26.29.114" in candidates
    assert "10.0.4.15" in candidates
    assert "127.0.0.1" in candidates

    # RFC 1918 Private Intranet
    private_ent = resolver.resolve("10.0.4.15", allow_online=False)
    assert private_ent is not None
    assert private_ent.type == "ip"
    assert "RFC 1918" in private_ent.details["Network Scope"]
    assert private_ent.metrics["is_private"] is True
    assert private_ent.badge == "INTERNAL RFC 1918"

    # Public Internet Endpoint
    public_ent = resolver.resolve("194.26.29.114", allow_online=False)
    assert public_ent is not None
    assert public_ent.type == "ip"
    assert "Public Internet" in public_ent.details["Network Scope"]
    assert public_ent.metrics["is_private"] is False
    assert public_ent.badge == "PUBLIC IP"


def test_hash_resolver_cryptographic_analysis():
    """Verifies HashResolver identifies algorithms, bit lengths, and null hashes."""
    from core.kb.resolvers.hash_resolver import HashResolver
    resolver = HashResolver()

    # MD5 Empty File NULL hash
    md5_null = "d41d8cd98f00b204e9800998ecf8427e"
    assert resolver.can_handle(md5_null) is True
    ent_md5 = resolver.resolve(md5_null, allow_online=False)
    assert ent_md5 is not None
    assert ent_md5.type == "hash"
    assert "MD5" in ent_md5.title
    assert "Empty File" in ent_md5.title
    assert ent_md5.metrics["bit_length"] == 128

    # SHA-256 Payload Hash
    sha256_hash = "5e884898da28047151d0e56f8dc6292773603d0d6aabbdd62a11ef721d1542d8"
    assert resolver.can_handle(sha256_hash) is True
    ent_sha = resolver.resolve(sha256_hash, allow_online=False)
    assert ent_sha is not None
    assert ent_sha.type == "hash"
    assert "SHA-256" in ent_sha.title
    assert ent_sha.metrics["bit_length"] == 256
    assert "Cryptographically Secure" in ent_sha.details["Security Status"]



