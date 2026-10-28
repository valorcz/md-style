"""
tests/test_inspector_cli.py
Unit tests for terminal Knowledge Base Inspector (kb-inspector),
terminal Markdown previewer, and rich logging integration.
"""

import io
from pathlib import Path
import pytest
from rich.console import Console

from core.inspector_cli import (
    load_knowledge_pack,
    find_entity,
    render_kb_overview_table,
    render_entity_card,
    inspect_cli_entrypoint,
)
from core.preview_cli import preview_markdown
from core.kb.models import KnowledgePack, Entity, Provenance, WidgetDescriptor
from core.diagnostics import Diagnostics, stdout_console, stderr_console


@pytest.fixture
def sample_pack():
    pack = KnowledgePack()
    ent = Entity(
        id="CVE-2024-3094",
        type="cve",
        domain="cyber",
        label="CVE-2024-3094",
        title="XZ Utils Backdoor Supply Chain Compromise",
        summary="Malicious backdoor discovered in upstream xz/liblzma tarballs leading to SSH auth bypass.",
        severity="CRITICAL",
        badge="SUPPLY CHAIN",
        attributes={
            "CVSS Score": "10.0 (CRITICAL)",
            "Vector": "Network / Remote Code Execution",
            "Affected Component": "liblzma 5.6.0, 5.6.1"
        },
        relationships=[
            {"target": "CWE-502", "relation": "categorized_as"},
            {"target": "T1059", "relation": "facilitates"}
        ],
        references=[
            {"title": "Openwall Advisory", "url": "https://www.openwall.com/lists/oss-security/2024/03/29/4"}
        ],
        widgets=[
            WidgetDescriptor(
                widget_type="tactical_box",
                title="Exploit Mechanics",
                data={
                    "items": [
                        "Stage 1: Modified m4 build scripts inject test payload",
                        "Stage 2: Hooked RSA_public_decrypt inside sshd"
                    ]
                }
            )
        ],
        provenance=Provenance(
            source="nvd:cve-dictionary",
            fetched_at="2026-10-15T12:00:00Z",
            status="resolved",
            manual_override=False
        )
    )
    pack.entities[ent.id] = ent
    return pack


def test_find_entity(sample_pack):
    # 1. Exact ID match
    ent1 = find_entity(sample_pack, "CVE-2024-3094")
    assert ent1 is not None
    assert ent1.id == "CVE-2024-3094"

    # 2. Case-insensitive match
    ent2 = find_entity(sample_pack, "cve-2024-3094")
    assert ent2 is not None

    # 3. Substring match
    ent3 = find_entity(sample_pack, "3094")
    assert ent3 is not None
    assert ent3.id == "CVE-2024-3094"

    # 4. Title match
    ent4 = find_entity(sample_pack, "XZ Utils")
    assert ent4 is not None

    # 5. Non-existent entity
    ent5 = find_entity(sample_pack, "NON-EXISTENT-XYZ")
    assert ent5 is None


def test_render_kb_overview_table(sample_pack):
    buf = io.StringIO()
    test_console = Console(file=buf, force_terminal=False, width=120)

    render_kb_overview_table(sample_pack, "test-doc.md", console=test_console)
    output = buf.getvalue()

    assert "Knowledge Pack Entities — test-doc.md" in output
    assert "CVE-2024-3094" in output
    assert "XZ Utils Backdoor" in output
    assert "CRITICAL" in output


def test_render_entity_card(sample_pack):
    buf = io.StringIO()
    test_console = Console(file=buf, force_terminal=False, width=120)

    ent = sample_pack.entities["CVE-2024-3094"]
    render_entity_card(ent, console=test_console)
    output = buf.getvalue()

    assert "XZ Utils Backdoor Supply Chain Compromise" in output
    assert "CVSS Score" in output
    assert "10.0 (CRITICAL)" in output
    assert "Exploit Mechanics" in output
    assert "Entity Relationships Graph" in output
    assert "CWE-502" in output
    assert "Openwall Advisory" in output
    assert "Provenance & Lineage" in output


def test_load_knowledge_pack_from_files(tmp_path, sample_pack):
    # 1. Test load from .json
    json_path = tmp_path / "test.kb.json"
    import json
    json_path.write_text(json.dumps(sample_pack.to_dict()), encoding="utf-8")

    loaded_pack = load_knowledge_pack(json_path)
    assert "CVE-2024-3094" in loaded_pack.entities

    # 2. Test load from .crate.zip
    import zipfile
    crate_path = tmp_path / "test.crate.zip"
    with zipfile.ZipFile(crate_path, "w") as zf:
        zf.writestr("report.kb.json", json.dumps(sample_pack.to_dict()))
        zf.writestr("ro-crate-metadata.json", "{}")

    loaded_crate_pack = load_knowledge_pack(crate_path)
    assert "CVE-2024-3094" in loaded_crate_pack.entities

    # 3. Test non-existent file
    with pytest.raises(FileNotFoundError):
        load_knowledge_pack(tmp_path / "missing.file")


def test_preview_markdown(tmp_path):
    md_content = """---
title: "Incident Forensic Report"
author: "Lead Forensic Investigator"
date: "2026-10-15"
style: forensic/cyber
abstract: "Comprehensive cyber threat analysis report regarding unauthorized network ingress."
---

# Incident Background

Suspicious lateral movement detected across perimeter infrastructure.

| Host | IP | Status |
| :--- | :--- | :--- |
| DC-01 | 10.0.4.15 | Compromised |
| WEB-02 | 10.0.4.20 | Clean |

- Immediate containment executed.
- Kerberos tickets invalidated.
"""
    doc_path = tmp_path / "report.md"
    doc_path.write_text(md_content, encoding="utf-8")

    buf = io.StringIO()
    test_console = Console(file=buf, force_terminal=False, width=120)

    preview_markdown(doc_path, use_pager=False, console=test_console)
    output = buf.getvalue()

    assert "Incident Forensic Report" in output
    assert "Lead Forensic Investigator" in output
    assert "EXECUTIVE SUMMARY" in output
    assert "Incident Background" in output
    assert "DC-01" in output
    assert "10.0.4.15" in output


def test_diagnostics_logging_with_rich():
    # Verify Diagnostics methods work without raising exceptions
    Diagnostics.info("Diagnostic info test")
    Diagnostics.success("Diagnostic success test")
    Diagnostics.warn("Diagnostic warn test")
    Diagnostics.error("Diagnostic error test")
    Diagnostics.debug_log("Detailed debug logging")


def test_html_bundle_detection_and_extraction(tmp_path):
    from core.bundler import is_md_style_html, extract_bundled_markdown, extract_bundled_knowledge_pack

    # 1. Generic HTML file
    generic_html = tmp_path / "generic.html"
    generic_html.write_text("<!DOCTYPE html><html><body><h1>Hello World</h1></body></html>", encoding="utf-8")
    assert is_md_style_html(generic_html) is False
    assert extract_bundled_markdown(generic_html) is None
    assert extract_bundled_knowledge_pack(generic_html) is None

    # 2. md-style bundled HTML file
    bundled_html = tmp_path / "report.html"
    sample_content = """<!DOCTYPE html>
<html lang="en">
<head>
  <meta name="generator" content="md-style v3.0 (pure-python)">
  <meta name="doc-fingerprint" content="abc123def456">
  <title>Sample Report</title>
</head>
<body>
  <div id="md-style-viewer-root"></div>
  <script id="md-style-source-markdown" type="text/markdown">
# Embedded Markdown Title

This is content inside the bundle.
  </script>
  <script id="md-style-kb-data" type="application/json">
{"@context": "https://schema.org", "entities": {"CVE-2024-3094": {"id": "CVE-2024-3094", "type": "cve"}}}
  </script>
</body>
</html>
"""
    bundled_html.write_text(sample_content, encoding="utf-8")

    assert is_md_style_html(bundled_html) is True
    extracted_md = extract_bundled_markdown(bundled_html)
    assert extracted_md is not None
    assert "Embedded Markdown Title" in extracted_md
    assert "This is content inside the bundle." in extracted_md

    extracted_kb = extract_bundled_knowledge_pack(bundled_html)
    assert extracted_kb is not None
    assert "CVE-2024-3094" in extracted_kb["entities"]

    # 3. Test preview on bundled HTML
    buf = io.StringIO()
    test_console = Console(file=buf, force_terminal=False, width=120)
    preview_markdown(bundled_html, use_pager=False, console=test_console)
    output = buf.getvalue()
    assert "Embedded Markdown Title" in output
    assert "Extracted from md-style HTML bundle" in output

    # 4. Test load_knowledge_pack from bundled HTML
    loaded_kb = load_knowledge_pack(bundled_html)
    assert "CVE-2024-3094" in loaded_kb.entities


def test_preview_from_ro_crate(tmp_path):
    import zipfile
    crate_path = tmp_path / "test.crate.zip"
    md_content = """---
title: "RO-Crate Document"
style: forensic/cyber
---

# RO-Crate Markdown

Payload extracted from archive.
"""
    with zipfile.ZipFile(crate_path, "w") as zf:
        zf.writestr("report.md", md_content)
        zf.writestr("ro-crate-metadata.json", "{}")

    buf = io.StringIO()
    test_console = Console(file=buf, force_terminal=False, width=120)
    preview_markdown(crate_path, use_pager=False, console=test_console)
    output = buf.getvalue()

    assert "RO-Crate Document" in output
    assert "RO-Crate Markdown" in output
    assert "Extracted from RO-Crate archive" in output


def test_preview_error_handling(tmp_path):
    # 1. Generic HTML file rejection
    generic_html = tmp_path / "generic.html"
    generic_html.write_text("<!DOCTYPE html><html><body><h1>Hello</h1></body></html>", encoding="utf-8")
    with pytest.raises(SystemExit) as exc_info:
        preview_markdown(generic_html)
    assert exc_info.value.code == 1

    # 2. Binary file rejection (null bytes)
    binary_file = tmp_path / "binary.dat"
    binary_file.write_bytes(b"\x00\x01\x02\x03\x04")
    with pytest.raises(SystemExit) as exc_info:
        preview_markdown(binary_file)
    assert exc_info.value.code == 1

    # 3. Non-existent file rejection
    with pytest.raises(SystemExit) as exc_info:
        preview_markdown(tmp_path / "non_existent.md")
    assert exc_info.value.code == 1

