"""
tests/test_cwe_resolver.py
Unit tests verifying CweResolver token handling, candidate extraction,
authoritative data resolution from data/cwe.json, Top 25 rank metadata,
and ATT&CK technique correlations.
"""

import pytest
from core.kb.resolvers.cwe_resolver import CweResolver


def test_cwe_resolver_can_handle():
    """Verifies CweResolver pattern recognition."""
    resolver = CweResolver()
    assert resolver.can_handle("CWE-787") is True
    assert resolver.can_handle("cwe-502") is True
    assert resolver.can_handle("CWE-289") is True
    assert resolver.can_handle("CVE-2024-21762") is False
    assert resolver.can_handle("T1190") is False

    candidates = resolver.extract_candidates("Document references CWE-787 and cwe-89 vulnerabilities.")
    assert "CWE-787" in candidates or "cwe-89" in candidates


def test_cwe_resolver_top25_enrichment():
    """Verifies CWE-787 (Out-of-bounds Write) resolves with Rank 1 and ATT&CK links."""
    resolver = CweResolver()
    ent = resolver.resolve("CWE-787", allow_online=False)
    assert ent is not None
    assert ent.id == "CWE-787"
    assert ent.type == "cwe"
    assert "Out-of-bounds Write" in ent.title
    assert ent.severity == "CRITICAL"
    assert ent.badge == "TOP 25 #1"
    assert ent.metrics.get("top25_rank") == 1
    assert "Modify Memory" in ent.details.get("Common Consequences", "")

    # Links to ATT&CK techniques
    targets = [r["target"] for r in ent.relationships if r["type"] == "mitre"]
    assert "T1190" in targets or "T1068" in targets


def test_cwe_resolver_deserialization():
    """Verifies CWE-502 (Deserialization of Untrusted Data) resolves with Rank 15."""
    resolver = CweResolver()
    ent = resolver.resolve("CWE-502", allow_online=False)
    assert ent is not None
    assert ent.id == "CWE-502"
    assert "Deserialization" in ent.title
    assert ent.metrics.get("top25_rank") == 15
    assert len(ent.details.get("Mitigation Strategy", "")) > 0

    targets = [r["target"] for r in ent.relationships if r["type"] == "mitre"]
    assert "T1190" in targets or "T1059" in targets


def test_cwe_resolver_offline_fallback():
    """Verifies clean fallback for uncataloged arbitrary CWE in offline mode."""
    resolver = CweResolver()
    ent = resolver.resolve("CWE-99999", allow_online=False)
    assert ent is not None
    assert ent.id == "CWE-99999"
    assert ent.type == "cwe"
    assert ent.provenance.status == "unresolved"
    assert "https://cwe.mitre.org/data/definitions/99999.html" in ent.references[0]["url"]
