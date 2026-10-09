"""
tests/test_style_remediation.py
Unit tests verifying style remediation features:
  1. TOC level filtering (--toc-levels)
  2. Frontmatter dossier header synthesis
  3. XDG standard user cache directory resolution
  4. SVJ agenda TOC card formatting
"""

import os
from pathlib import Path
from core.config import get_user_cache_dir
from core.parser.plugins.toc import render_toc_html
from core.i18n import I18nCatalog
from core.engine import ReportEngine, PipelineConfig

def test_user_cache_dir_xdg_linux():
    """Verifies cache directory adheres to XDG on Linux or standard platform dirs."""
    cache_dir = get_user_cache_dir()
    assert cache_dir.name == "md-style"
    # On linux, should contain .cache
    if os.name == "posix":
        assert ".cache" in str(cache_dir)

def test_toc_levels_filtering():
    """Verifies TOC generator filters headings according to specified levels."""
    headings = [
        {"id": "h1-first", "title": "Heading 1", "level": 1},
        {"id": "h2-first", "title": "Heading 2", "level": 2},
        {"id": "h3-first", "title": "Heading 3", "level": 3},
        {"id": "h2-second", "title": "Heading 2.2", "level": 2},
    ]

    # Filter only level 2
    html_lvl2 = render_toc_html(headings, catalog=I18nCatalog("cs"), levels=[2])
    assert "Heading 2" in html_lvl2
    assert "Heading 2.2" in html_lvl2
    assert "Heading 1" not in html_lvl2
    assert "Heading 3" not in html_lvl2

    # Filter levels 1 and 2
    html_lvl12 = render_toc_html(headings, catalog=I18nCatalog("cs"), levels=[1, 2])
    assert "Heading 1" in html_lvl12
    assert "Heading 2" in html_lvl12
    assert "Heading 3" not in html_lvl12

def test_svj_agenda_toc_card_format():
    """Verifies SVJ theme formats TOC as .agenda-toc-container card."""
    headings = [
        {"id": "bod-1", "title": "1. Zahájení", "level": 2},
        {"id": "bod-2", "title": "2. Zpráva výboru", "level": 2},
    ]

    html = render_toc_html(headings, catalog=I18nCatalog("cs"), style_family="svj/invitation", levels=[2])
    assert 'class="agenda-toc-container"' in html
    assert '<div class="toc-title">Program shromáždění</div>' in html
    assert 'href="#bod-1"' in html
    assert 'href="#bod-2"' in html

def test_dossier_header_synthesis():
    """Verifies automatic synthesis of #title-block-header from frontmatter for forensic documents."""
    cfg = PipelineConfig(
        input_file=Path("/tmp/fake.md"),
        output_file=Path("/tmp/fake.html"),
        style="forensic/cyber",
        quiet=True
    )
    engine = ReportEngine(cfg)

    fm = {
        "title": "Incident DFIR Report",
        "subtitle": "Analysis of host DC-CORP-01",
        "examiner": "Lead Analyst J. Doe",
        "date": "2026-10-09",
        "case_id": "IR-2026-99",
        "abstract": "The suspect binary was successfully isolated.",
        "report_badge": "CLASSIFIED REPORT"
    }

    assert engine._should_build_dossier_header("forensic/cyber", fm) is True

    cat = I18nCatalog("en")
    header_html = engine._build_dossier_header(fm, fm["title"], cat)
    assert '<header id="title-block-header"' in header_html
    assert 'Incident DFIR Report' in header_html
    assert 'Analysis of host DC-CORP-01' in header_html
    assert 'Lead Analyst J. Doe' in header_html
    assert 'IR-2026-99' in header_html
    assert 'The suspect binary was successfully isolated.' in header_html
    assert 'CLASSIFIED REPORT' in header_html

def test_filter_toc_by_section():
    """Verifies filter_toc_by_section isolates children under the target heading."""
    from core.parser.plugins.toc import filter_toc_by_section

    headings = [
        {"id": "meta", "title": "Termín a místo konání", "level": 2},
        {"id": "agenda", "title": "Program shromáždění", "level": 2},
        {"id": "details", "title": "Detaily jednání", "level": 2},
        {"id": "b1", "title": "1. Zahájení", "level": 3},
        {"id": "b2", "title": "2. Hospodaření", "level": 3},
        {"id": "closing", "title": "Závěr a podpisy", "level": 2},
    ]

    filtered = filter_toc_by_section(headings, "Detaily jednání")
    assert len(filtered) == 2
    assert filtered[0]["id"] == "b1"
    assert filtered[1]["id"] == "b2"

def test_svj_agenda_toc_section_scoping_and_num_stripping():
    """Verifies SVJ theme defaults TOC to 'Detaily jednání' and strips duplicate leading numbers."""
    headings = [
        {"id": "meta", "title": "Termín a místo konání", "level": 2},
        {"id": "agenda", "title": "Program shromáždění", "level": 2},
        {"id": "details", "title": "Detaily jednání", "level": 2},
        {"id": "b1", "title": "1. Zahájení a volba orgánů", "level": 3},
        {"id": "b2", "title": "2. Zpráva o hospodaření", "level": 3},
        {"id": "closing", "title": "Závěr", "level": 2},
    ]

    # Without explicit section attribute, SVJ automatically scopes to 'Detaily jednání'
    html = render_toc_html(headings, catalog=I18nCatalog("cs"), style_family="svj/invitation")
    assert "Termín a místo" not in html
    assert "Program shromáždění</a>" not in html
    assert "Zahájení a volba orgánů" in html
    assert "Zpráva o hospodaření" in html
    # Ensure leading "1. " was stripped from title inside <a> so <ol> handles numbering
    assert ">Zahájení a volba orgánů</a>" in html
    assert ">1. Zahájení" not in html

def test_table_timestamp_and_hash_detection():
    """Verifies table transform auto-detects timestamps (nowrap) and cryptographic hashes (break-all)."""
    from core.parser import MarkdownParser

    src = """
| Time | SHA-256 | Description |
| --- | --- | --- |
| 2026-10-09 14:22:15 UTC | `a1b2c3d4e5f60718293a4b5c6d7e8f90a1b2c3d4e5f60718293a4b5c6d7e8f90` | Initial beacon |
"""
    p = MarkdownParser(lang="en")
    html_out, _, _ = p.render(src)
    assert 'class="timestamp nowrap"' in html_out
    assert 'class="hash break-all"' in html_out

def test_bundler_embed_source_markdown(tmp_path):
    """Verifies AssetBundler embeds raw markdown into <script id="md-style-source-markdown">."""
    from core.bundler import AssetBundler
    from core.themes import ThemeResolver

    doc_path = tmp_path / "fake-report.md"
    doc_path.write_text("# Test\n", encoding="utf-8")

    resolver = ThemeResolver()
    theme = resolver.resolve("forensic/cyber")

    bundler = AssetBundler(doc_path=doc_path)
    sample_md = "# Incident Dossier\n\n```python\nprint('test')\n```"
    html = bundler.assemble(
        html_fragment="<article>content</article>",
        theme=theme,
        title="Test Report",
        raw_markdown=sample_md,
    )
    assert '<script id="md-style-source-markdown" type="text/markdown">' in html
    assert '# Incident Dossier' in html
    assert 'print(\'test\')' in html

def test_cli_embed_source_flag():
    """Verifies CLI parser properly defaults and toggles --embed-source / --no-embed-source."""
    from core.cli import build_parser

    parser = build_parser()
    args_default = parser.parse_args(["input.md"])
    assert args_default.embed_source is True

    args_disabled = parser.parse_args(["input.md", "--no-embed-source"])
    assert args_disabled.embed_source is False

    args_enabled = parser.parse_args(["input.md", "--embed-source"])
    assert args_enabled.embed_source is True
