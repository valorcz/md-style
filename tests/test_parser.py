"""
tests/test_parser.py
Unit tests for pure-Python Markdown parser and AST transforms.
"""

from core.parser import MarkdownParser
from core.kb.models import KnowledgePack, Entity

def test_callouts_transform():
    p = MarkdownParser(lang="en")
    src = "> [!WARNING] Threat Detected\n> Adversary activity observed."
    html_out, _, _ = p.render(src)

    assert 'class="callout callout-warning' in html_out
    assert 'Threat Detected' in html_out
    assert 'Adversary activity observed.' in html_out

def test_tables_transform_with_wbr():
    p = MarkdownParser(lang="en")
    src = """
| Timestamp | Host |
| --- | --- |
| 2026-09-29 10:00:00 - 2026-09-29 12:00:00 | DC-01 |
"""
    html_out, _, _ = p.render(src)

    assert '<div class="table-wrapper">' in html_out
    assert '<span class="time-range' in html_out
    assert '<wbr>' in html_out

def test_inspectable_entities_tagging():
    p = MarkdownParser(lang="en")
    pack = KnowledgePack()
    pack.entities["CVE-2024-21413"] = Entity(
        id="CVE-2024-21413", domain="cyber", type="cve",
        label="CVE-2024-21413", title="Outlook RCE", severity="CRITICAL"
    )

    src = "Identified `CVE-2024-21413` in execution logs and CVE-2024-21413 in prose."
    html_out, _, _ = p.render(src, knowledge_pack=pack)

    assert 'data-token="CVE-2024-21413"' in html_out
    assert 'class="inspectable inspectable-critical"' in html_out

def test_validate_input_file(tmp_path):
    import pytest
    from pathlib import Path
    from core.engine import validate_input_file

    # 1. Valid markdown file
    valid_md = tmp_path / "valid.md"
    valid_md.write_text("# Hello World\nThis is a report.", encoding="utf-8")
    validate_input_file(valid_md)  # Should not raise

    # 2. Disallowed extension: .pdf
    pdf_file = tmp_path / "doc.pdf"
    pdf_file.write_bytes(b"%PDF-1.4 binary data")
    with pytest.raises(ValueError, match="Unsupported input file format"):
        validate_input_file(pdf_file)

    # 3. Disallowed extension: .html
    html_file = tmp_path / "index.html"
    html_file.write_text("<!DOCTYPE html><html><body>Report</body></html>", encoding="utf-8")
    with pytest.raises(ValueError, match="Unsupported input file format"):
        validate_input_file(html_file)

    # 4. Binary file disguised as .md (contains null bytes)
    fake_md = tmp_path / "fake.md"
    fake_md.write_bytes(b"Header\x00\x01\x02BinaryData")
    with pytest.raises(ValueError, match="appears to be a binary file"):
        validate_input_file(fake_md)

    # 5. Raw HTML disguised as .txt
    raw_html_txt = tmp_path / "report.txt"
    raw_html_txt.write_text("<!DOCTYPE html>\n<html><head></head><body>Raw HTML</body></html>", encoding="utf-8")
    with pytest.raises(ValueError, match="appears to be raw HTML"):
        validate_input_file(raw_html_txt)

    # 6. Non-existent file
    non_existent = tmp_path / "non_existent.md"
    with pytest.raises(FileNotFoundError):
        validate_input_file(non_existent)

