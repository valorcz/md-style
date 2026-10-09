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
