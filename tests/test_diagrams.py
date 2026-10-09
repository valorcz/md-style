"""
tests/test_diagrams.py
Validates beautiful-mermaid compilation, CLI diagnostics on syntax errors,
figure localization, and Markdown-It fence plugin integration.
"""

import pytest
from pathlib import Path
from core.diagrams.mermaid import MermaidRenderer
from core.parser.engine import MarkdownParser
from core.config import VIEWER_DIR, MERMAID_SCRIPT

def test_vendor_directory_eliminated():
    """Confirms vendor/ directory is removed and scripts are in viewer/."""
    vendor_dir = Path(__file__).resolve().parent.parent / "vendor"
    assert not vendor_dir.exists(), "vendor/ directory must be completely removed"
    assert MERMAID_SCRIPT.exists(), f"render script must exist at {MERMAID_SCRIPT}"

def test_beautiful_mermaid_static_svg():
    """Tests successful build-time SVG compilation using beautiful-mermaid."""
    renderer = MermaidRenderer()
    code = "flowchart TD\n    A[Start] --> B[End]"
    html_out, is_fallback = renderer.render_figure(
        code=code,
        id_attr="fig-test-flowchart",
        caption="Figure 1: Flowchart Test",
        lang="en"
    )

    assert not is_fallback, "Should compile directly to static SVG when node is available"
    assert 'data-engine="beautiful-mermaid"' in html_out
    assert "<svg" in html_out
    assert 'id="fig-test-flowchart"' in html_out
    assert '<figcaption class="mermaid-caption">' in html_out
    assert "Figure 1:" in html_out

def test_invalid_syntax_error_handling(capsys):
    """Verifies that invalid Mermaid syntax logs an explicit error and falls back gracefully."""
    renderer = MermaidRenderer()
    broken_code = "flowchart TD; broken syntax ::::"

    html_out, is_fallback = renderer.render_figure(
        code=broken_code,
        id_attr="fig-broken",
        line_no=99
    )

    captured = capsys.readouterr()
    assert is_fallback, "Invalid syntax should trigger fallback container"
    assert 'data-engine="client"' in html_out
    assert "fig-broken" in captured.err or "render error" in captured.err or "Invalid mermaid header" in captured.err

def test_localized_figure_captions():
    """Verifies figure caption localized labels."""
    renderer = MermaidRenderer()
    cs_caption = renderer.format_caption("Architektura systému", lang="cs", count=1)
    assert "Obrázek 1:" in cs_caption

    en_caption = renderer.format_caption("System Architecture", lang="en", count=2)
    assert "Figure 2:" in en_caption

def test_markdown_it_fence_plugin_no_mangling():
    """Verifies that 4-space indented lines in sequence diagrams are not mangled into pre/code by CommonMark."""
    md_content = """# Report

``` {.mermaid #fig-seq caption="Figure 1: Sequence"}
sequenceDiagram
    autonumber
    participant A as Alice
    participant B as Bob
    A->>B: Hello Bob
```
"""
    parser = MarkdownParser(lang="en", enable_mermaid=True)
    html_frag, _, _ = parser.render(md_content)

    assert 'id="fig-seq"' in html_frag
    assert "<svg" in html_frag or 'data-engine="client"' in html_frag
    # Critical check: CommonMark must NOT have wrapped inner statements in <pre><code>
    assert "autonumber\n<pre><code>" not in html_frag
    assert "&amp;gt;&amp;gt;" not in html_frag
