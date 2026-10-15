"""
tests/test_callout_plugin.py
Unit tests for unified callouts plugin (GitHub alerts and container callouts).
"""

from core.parser import MarkdownParser
from core.i18n import I18nCatalog

def test_github_alert_custom_title():
    p = MarkdownParser()
    src = """
> [!CRITICAL] Immediate Domain Quarantine
> Active C2 beaconing observed.
"""
    html_out, _, _ = p.render(src)
    assert 'class="callout callout-critical critical"' in html_out
    assert 'Immediate Domain Quarantine' in html_out
    assert '<svg class="callout-icon"' in html_out

def test_container_callout():
    p = MarkdownParser()
    src = """
::: warning Suspicious Memory Dump
Found unlinked executable memory segment.
:::
"""
    html_out, _, _ = p.render(src)
    assert 'class="callout callout-warning warning"' in html_out
    assert 'Suspicious Memory Dump' in html_out

def test_dfir_alert_types():
    p = MarkdownParser()
    src = """
> [!EVIDENCE] Hard Drive Bitstream
> SHA256 verified.

> [!FINDING] Lateral Movement
> SMB traversal confirmed.
"""
    html_out, _, _ = p.render(src)
    assert 'class="callout callout-evidence evidence"' in html_out
    assert 'class="callout callout-finding finding"' in html_out

def test_callout_inline_markdown_preserved():
    """Verifies that rich inline markdown (bold, code, links) is preserved inside callouts."""
    p = MarkdownParser()
    src = """
> [!NOTE] Timezone Notice
> All timestamps in this section are in **UTC** (Coordinated Universal Time), unless noted as `CET`.
"""
    html_out, _, _ = p.render(src)
    assert 'class="callout callout-note note"' in html_out
    assert 'Timezone Notice' in html_out
    assert '<strong>UTC</strong>' in html_out
    assert '<code>CET</code>' in html_out

def test_callout_legacy_bold_format():
    """Verifies legacy format (> **WARNING**: ...) is converted to styled callouts with code preserved."""
    p = MarkdownParser()
    src = """
> **WARNING**: The binary disguise `ntdll_bk.dll` was placed into `C:\\Windows\\Temp`.
"""
    html_out, _, _ = p.render(src)
    assert 'class="callout callout-warning warning"' in html_out
    assert '<code>ntdll_bk.dll</code>' in html_out
    assert '<code>C:\\Windows\\Temp</code>' in html_out

def test_nested_callout_alerts():
    """Verifies recursive parsing of nested callout blockquotes."""
    p = MarkdownParser()
    src = """
> [!NOTE] Outer Note
> Outer body text
> 
> > [!WARNING] Inner Warning
> > Inner body text
"""
    html_out, _, _ = p.render(src)
    assert 'class="callout callout-note note"' in html_out
    assert 'class="callout callout-warning warning"' in html_out
    assert 'Outer Note' in html_out
    assert 'Inner Warning' in html_out
    assert 'Outer body text' in html_out
    assert 'Inner body text' in html_out
    # Outer note must contain inner warning
    note_pos = html_out.find('callout-note')
    warn_pos = html_out.find('callout-warning')
    assert 0 <= note_pos < warn_pos

def test_deeply_nested_callout_alerts_3_levels():
    """Verifies that arbitrary callout nesting depth (3+ levels) functions cleanly."""
    p = MarkdownParser()
    src = """
> [!NOTE] Level 1 Note
> > [!WARNING] Level 2 Warning
> > > [!CRITICAL] Level 3 Critical
"""
    html_out, _, _ = p.render(src)
    assert 'callout-note' in html_out
    assert 'callout-warning' in html_out
    assert 'callout-critical' in html_out
    idx1 = html_out.find('callout-note')
    idx2 = html_out.find('callout-warning')
    idx3 = html_out.find('callout-critical')
    assert 0 <= idx1 < idx2 < idx3

def test_single_line_callout_title_deduplication():
    """Verifies that single-line alerts do not duplicate their custom title in the body paragraph."""
    p = MarkdownParser()
    src = "> [!NOTE] Dedicated Custom Title"
    html_out, _, _ = p.render(src)
    assert '<span class="callout-title">Dedicated Custom Title</span>' in html_out
    assert '<p>Dedicated Custom Title</p>' not in html_out

def test_single_line_callout_multi_paragraph_deduplication():
    """Verifies that a title line separated by a blank line does not duplicate in callout content."""
    p = MarkdownParser()
    src = """
> [!NOTE] Custom Header
>
> Body paragraph content.
"""
    html_out, _, _ = p.render(src)
    assert '<span class="callout-title">Custom Header</span>' in html_out
    assert '<p>Custom Header</p>' not in html_out
    assert '<p>Body paragraph content.</p>' in html_out

def test_callout_with_standard_blockquote_inside():
    """Verifies that regular blockquotes inside a callout remain rendered as standard blockquotes."""
    p = MarkdownParser()
    src = """
> [!NOTE] Callout Header
>
> > Normal quote content
"""
    html_out, _, _ = p.render(src)
    assert 'callout-note' in html_out
    assert '<blockquote>' in html_out
    assert 'Normal quote content' in html_out

def test_standard_blockquote_with_nested_callout():
    """Verifies that a callout nested inside a standard blockquote is properly transformed."""
    p = MarkdownParser()
    src = """
> Normal quote
>
> > [!WARNING] Nested Alert
> > Watch out
"""
    html_out, _, _ = p.render(src)
    assert '<blockquote>' in html_out
    assert 'callout-warning' in html_out
    assert 'Watch out' in html_out
