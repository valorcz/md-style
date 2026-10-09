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
