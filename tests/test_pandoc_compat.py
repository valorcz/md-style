"""
tests/test_pandoc_compat.py
Unit tests for Pandoc markup compatibility (fenced divs, bracketed spans, TOC inlining, and proposals).
"""

from core.parser import MarkdownParser
from core.i18n import I18nCatalog

def test_bracketed_spans():
    p = MarkdownParser()
    src = "Found [MALICIOUS]{.badge .badge-critical} and [Elena Rostova]{.dossier-value}."
    html_out, _, _ = p.render(src)

    assert '<span class="badge badge-critical">MALICIOUS</span>' in html_out
    assert '<span class="dossier-value">Elena Rostova</span>' in html_out

def test_pandoc_fenced_divs():
    p = MarkdownParser()
    src = """
::: {.kpi-grid}
### 14
Compromised Endpoints
:::

::: {.ai-insight confidence="99.4%" agent="SENTINEL-9"}
Neural analysis complete.
:::
"""
    html_out, _, _ = p.render(src)

    assert '<div class="kpi-grid">' in html_out
    assert 'class="ai-insight"' in html_out
    assert 'confidence="99.4%"' in html_out
    assert 'agent="SENTINEL-9"' in html_out

def test_nested_fenced_divs():
    p = MarkdownParser()
    src = """
:::: {.outer-card}
::: {.inner-badge}
Nested Content
:::
::::
"""
    html_out, _, _ = p.render(src)
    assert '<div class="outer-card">' in html_out
    assert '<div class="inner-badge">' in html_out

def test_toc_inlining():
    p = MarkdownParser()
    src = """
# Main Document Title

[[TOC]]

## Section Alpha
Alpha text.

## Section Beta
Beta text.
"""
    html_out, toc, _ = p.render(src)

    assert '<nav id="toc" class="table-of-contents"' in html_out
    assert 'href="#section-alpha"' in html_out
    assert 'href="#section-beta"' in html_out
    assert 'Section Alpha' in html_out
    assert 'Section Beta' in html_out

def test_proposal_callout_with_ballot():
    cat_cs = I18nCatalog("cs")
    p = MarkdownParser(lang="cs", catalog=cat_cs)
    src = """
::: proposal Schválení rozpočtu na rok 2026
Výbor navrhuje schválit rozpočet ve výši 500 000 Kč.
:::
"""
    html_out, _, _ = p.render(src)

    assert 'class="callout callout-proposal-callout proposal-callout"' in html_out
    assert 'Schválení rozpočtu na rok 2026' in html_out
    assert 'class="proposal-ballot"' in html_out
    assert 'HLASOVÁNÍ:' in html_out
    assert 'PRO' in html_out
    assert 'PROTI' in html_out
    assert 'ZDRŽEL SE' in html_out
