"""
tests/test_kb_lifecycle.py
Unit tests for Knowledge Pack lifecycle, provenance, and refresh behaviors.
"""

import json
import pytest
from pathlib import Path
from core.kb.models import KnowledgePack, Entity, Provenance
from core.kb.lifecycle import KnowledgeLifecycleManager

def test_manual_override_preservation(tmp_path):
    doc_path = tmp_path / "test_report.md"
    doc_path.write_text("# Case Report\nAdversary used CVE-2024-21413.", encoding="utf-8")

    mgr = KnowledgeLifecycleManager(doc_path)

    # Initial sync
    pack = mgr.sync(doc_path.read_text(), refresh_mode="incremental", allow_online=False)
    assert "CVE-2024-21413" in pack.entities

    # Analyst manually edits entity title and sets manual_override
    ent = pack.entities["CVE-2024-21413"]
    ent.title = "Analyst Custom Note: Critical Zero-Day Target"
    ent.provenance = Provenance(source="analyst:manual", manual_override=True)
    mgr.save_pack()

    # Second sync with force refresh
    mgr2 = KnowledgeLifecycleManager(doc_path)
    pack2 = mgr2.sync(doc_path.read_text(), refresh_mode="force", allow_online=False)

    assert pack2.entities["CVE-2024-21413"].title == "Analyst Custom Note: Critical Zero-Day Target"
    assert pack2.entities["CVE-2024-21413"].provenance.manual_override is True

def test_source_digest_tracking(tmp_path):
    doc_path = tmp_path / "report.md"
    doc_path.write_text("# Test\n", encoding="utf-8")

    src_file = tmp_path / "assets.json"
    src_file.write_text(json.dumps([{"id": "SRV-01", "title": "Database Server"}]), encoding="utf-8")

    frontmatter = {
        "knowledge": {
            "sources": [{"type": "json", "path": str(src_file)}]
        }
    }

    mgr = KnowledgeLifecycleManager(doc_path)
    pack = mgr.sync(doc_path.read_text(), frontmatter=frontmatter)

    assert "SRV-01" in pack.entities
    assert str(src_file) in pack.sources_digest
    digest1 = pack.sources_digest[str(src_file)]

    # Update source file
    src_file.write_text(json.dumps([{"id": "SRV-01", "title": "Updated DB Server"}]), encoding="utf-8")

    # Refresh
    mgr2 = KnowledgeLifecycleManager(doc_path)
    pack2 = mgr2.sync(doc_path.read_text(), frontmatter=frontmatter, refresh_mode="incremental")
    digest2 = pack2.sources_digest[str(src_file)]

    assert digest1 != digest2
    assert pack2.entities["SRV-01"].title == "Updated DB Server"


def test_transitive_graph_closure(tmp_path):
    """Verifies that KnowledgeLifecycleManager performs transitive expansion from GHSA to CVE."""
    doc_path = tmp_path / "forensic_report.md"
    doc_path.write_text(
        "# Advisory\nSecurity alert referenced GHSA-jfh8-c2jp-5v3q in telemetry log.",
        encoding="utf-8"
    )

    mgr = KnowledgeLifecycleManager(doc_path)
    pack = mgr.sync(doc_path.read_text(), allow_online=False)

    # 1. GHSA must be resolved from prose
    assert "GHSA-JFH8-C2JP-5V3Q" in pack.entities
    ghsa_ent = pack.entities["GHSA-JFH8-C2JP-5V3Q"]
    assert ghsa_ent.type == "ghsa"

    # 2. Transitive CVE-2021-44228 must be resolved automatically
    assert "CVE-2021-44228" in pack.entities
    cve_ent = pack.entities["CVE-2021-44228"]
    assert cve_ent.type == "cve"
    assert cve_ent.provenance.source == "transitive:GHSA-JFH8-C2JP-5V3Q"
    assert cve_ent.provenance.details.get("discovered_via") == "GHSA-JFH8-C2JP-5V3Q"

    # 3. Bidirectional link verification
    # GHSA links to CVE
    ghsa_targets = [r["target"] for r in ghsa_ent.relationships]
    assert "CVE-2021-44228" in ghsa_targets

    # CVE links back to GHSA
    cve_targets = [r["target"] for r in cve_ent.relationships]
    assert "GHSA-JFH8-C2JP-5V3Q" in cve_targets
    backlink = next(r for r in cve_ent.relationships if r["target"] == "GHSA-JFH8-C2JP-5V3Q")
    assert backlink["relation"] == "referenced_by"


def test_transitive_cve_to_cwe_expansion(tmp_path):
    """Verifies that KnowledgeLifecycleManager transitively resolves CWE-787 from CVE-2024-21762."""
    doc_path = tmp_path / "cve_report.md"
    doc_path.write_text("# Case Note\nSystem was impacted by CVE-2024-21762 vulnerability.", encoding="utf-8")

    mgr = KnowledgeLifecycleManager(doc_path)
    pack = mgr.sync(doc_path.read_text(), allow_online=False)

    assert "CVE-2024-21762" in pack.entities
    assert "CWE-787" in pack.entities

    cwe_ent = pack.entities["CWE-787"]
    assert cwe_ent.type == "cwe"
    assert cwe_ent.provenance.source == "transitive:CVE-2024-21762"
    assert "Out-of-bounds Write" in cwe_ent.title
    assert cwe_ent.metrics.get("top25_rank") == 1

    # Bidirectional links
    cve_ent = pack.entities["CVE-2024-21762"]
    assert any(r["target"] == "CWE-787" for r in cve_ent.relationships)
    assert any(r["target"] == "CVE-2024-21762" and r["relation"] == "referenced_by" for r in cwe_ent.relationships)


def test_evtx_deduplication_and_alias_aggregation(tmp_path):
    """Verifies that multiple path representations of the same EVTX channel deduplicate to 1 canonical entity with aliases."""
    doc_path = tmp_path / "forensic_channels.md"
    doc_path.write_text(
        "# Windows Logs\n"
        "Artifact extracted from `%SystemRoot%\\System32\\Winevt\\Logs\\Sysmon.evtx`.\n"
        "Further telemetry inspected in `Sysmon.evtx` and `System32\\Winevt\\Logs\\Sysmon.evtx`.\n",
        encoding="utf-8"
    )

    mgr = KnowledgeLifecycleManager(doc_path)
    pack = mgr.sync(doc_path.read_text(), allow_online=False)

    # Exactly 1 Sysmon entity should exist in the pack
    sysmon_entities = [e for e in pack.entities.values() if e.type == "evtx"]
    assert len(sysmon_entities) == 1

    sysmon = sysmon_entities[0]
    assert sysmon.id == "Sysmon.evtx"
    assert "Microsoft Sysmon" in sysmon.title

    # Aliases should aggregate all variations mentioned
    assert any("Winevt" in a for a in sysmon.aliases)
    assert "Sysmon.evtx" in sysmon.aliases



