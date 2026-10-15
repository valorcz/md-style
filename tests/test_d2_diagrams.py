"""
tests/test_d2_diagrams.py
Unit tests verifying D2 diagram renderer, caption formatting, theme mapping,
and MarkdownParser integration.
"""

from core.diagrams.d2 import D2Renderer
from core.parser.engine import MarkdownParser
from core.i18n import I18nCatalog


def test_d2_renderer_theme_mapping():
    """Verifies D2Renderer maps document themes to correct D2 theme codes."""
    renderer = D2Renderer()
    assert renderer._resolve_d2_theme("forensic/cyber") == "301"
    assert renderer._resolve_d2_theme("cyber-dark") == "301"
    assert renderer._resolve_d2_theme("forensic/dossier") == "3"
    assert renderer._resolve_d2_theme("svj/base") == "0"
    assert renderer._resolve_d2_theme("general/school") == "4"


def test_d2_renderer_caption_formatting():
    """Verifies D2 figure captions are formatted with localized labels and numbering."""
    renderer = D2Renderer()
    cap_en = renderer.format_caption("Network Architecture", lang="en", count=1)
    assert "Figure 1:" in cap_en
    assert "Network Architecture" in cap_en

    cap_cs = renderer.format_caption("Schéma sítě", lang="cs", count=2)
    assert "Obrázek 2:" in cap_cs
    assert "Schéma sítě" in cap_cs


def test_d2_renderer_fallback_html():
    """Verifies D2Renderer emits a semantic figure container with fallback code block."""
    renderer = D2Renderer()
    # Force fallback branch by temporarily setting _binary = None
    orig_bin = renderer._binary
    try:
        renderer._binary = None
        html_out, is_fallback = renderer.render_figure(
            code="x -> y: hello",
            id_attr="fig-test",
            caption="Test D2 Flow",
            lang="en",
            theme="base"
        )
        assert is_fallback is True
        assert 'id="fig-test"' in html_out
        assert 'class="d2-diagram d2-fallback"' in html_out
        assert 'data-engine="fallback"' in html_out
        assert 'x -&gt; y: hello' in html_out or 'x -> y: hello' in html_out
        assert '<figcaption class="d2-caption">' in html_out
    finally:
        renderer._binary = orig_bin


def test_markdown_parser_with_d2_block():
    """Verifies MarkdownParser processes fenced d2 blocks into figure containers."""
    parser = MarkdownParser(lang="en", theme_name="zinc-light")
    md_content = """# System Architecture

```d2 #arch-diagram caption="Service Topology"
serviceA -> serviceB: HTTP JSON
serviceB -> database: SQL Query
```
"""
    html_frag, toc, meta = parser.render(md_content)
    assert '<figure class="d2-diagram' in html_frag
    assert 'id="arch-diagram"' in html_frag
    assert 'Service Topology' in html_frag
    assert parser.d2_renderer.figure_count == 1
