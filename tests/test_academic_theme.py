"""
tests/test_academic_theme.py
Tests for the academic/lecture teaching theme, FI MUNI visual identity,
auto-ToC suppression, and clean running headers/footers.
"""

from pathlib import Path
import pytest
from core.themes import ThemeResolver
from core.engine import ReportEngine, PipelineConfig
from core.bundler import AssetBundler
from core.i18n import I18nCatalog


def test_academic_theme_discovery_and_aliases():
    """Verifies that academic/lecture resolves cleanly and all aliases point to it."""
    resolver = ThemeResolver()

    canonical = resolver.resolve("academic/lecture")
    assert canonical.name == "academic/lecture"
    assert "base" in canonical.inheritance_chain
    assert canonical.features.get("auto_toc") is False
    assert canonical.features.get("interactive_viewer") is True
    assert canonical.features.get("callouts") is True

    # Check FI MUNI colors & typography variables
    vars_dict = canonical.variables
    assert vars_dict.get("--color-muni-blue") == "#0000dc"
    assert vars_dict.get("--color-fi-saffron") == "#f2d45c"
    assert "Source Serif 4" in vars_dict.get("--font-serif", "")
    assert "Inter" in vars_dict.get("--font-sans", "")

    # Test all registered aliases
    for alias in ["academic", "lecture", "teaching", "fi-muni", "muni"]:
        resolved = resolver.resolve(alias)
        assert resolved.name == "academic/lecture", f"Alias '{alias}' did not resolve to 'academic/lecture'"


def test_academic_theme_auto_toc_suppression(tmp_path):
    """Verifies that academic/lecture suppresses auto-TOC when no [[TOC]] placeholder exists."""
    md_content = """# First Lecture Section
Some introductory text.

## Subsection A
More details.

## Subsection B
Further explanation.
"""
    doc_path = tmp_path / "test_lecture.md"
    doc_path.write_text(md_content, encoding="utf-8")
    out_path = tmp_path / "test_lecture.html"

    config = PipelineConfig(
        input_file=doc_path,
        output_file=out_path,
        style="academic/lecture",
    )
    engine = ReportEngine(config)
    engine.run()

    html = out_path.read_text(encoding="utf-8")
    assert '<nav id="toc"' not in html
    assert 'class="table-of-contents"' not in html


def test_academic_theme_explicit_toc_override(tmp_path):
    """Verifies that explicit frontmatter toc: true or [[TOC]] renders a TOC even in academic theme."""
    # 1. Via frontmatter toc: true
    md_fm = """---
title: "Lecture with Explicit TOC"
style: "academic/lecture"
toc: true
---

# Topic 1
Content 1.

## Subtopic 1.1
Details.
"""
    doc_path = tmp_path / "explicit_toc.md"
    doc_path.write_text(md_fm, encoding="utf-8")
    out_path = tmp_path / "explicit_toc.html"

    config = PipelineConfig(input_file=doc_path, output_file=out_path)
    engine = ReportEngine(config)
    engine.run()

    html = out_path.read_text(encoding="utf-8")
    assert '<nav id="toc"' in html

    # 2. Via explicit [[TOC]] placeholder
    md_placeholder = """# Topic A

[[TOC]]

## Section A1
Text A1.
"""
    doc2_path = tmp_path / "placeholder_toc.md"
    doc2_path.write_text(md_placeholder, encoding="utf-8")
    out2_path = tmp_path / "placeholder_toc.html"

    config2 = PipelineConfig(
        input_file=doc2_path,
        output_file=out2_path,
        style="academic/lecture",
    )
    engine2 = ReportEngine(config2)
    engine2.run()

    html2 = out2_path.read_text(encoding="utf-8")
    assert '<nav id="toc"' in html2


def test_academic_theme_paged_header_and_footer(tmp_path):
    """Verifies that Paged print headers/footers contain clean academic info without forensic stamps."""
    resolver = ThemeResolver()
    theme = resolver.resolve("academic/lecture")
    catalog = I18nCatalog("cs")
    bundler = AssetBundler(doc_path=tmp_path / "dummy.md")

    frontmatter = {
        "title": "Programování v jazyce C",
        "course": "PB071",
        "term": "Jaro 2026",
        "institution": "Fakulta informatiky MU",
    }

    cdp_templates = bundler.build_cdp_header_footer_templates(
        theme=theme,
        catalog=catalog,
        title="Programování v jazyce C",
        frontmatter=frontmatter,
        fingerprint="abcdef1234567890",
    )

    header = cdp_templates["headerTemplate"]
    footer = cdp_templates["footerTemplate"]

    # Header checks
    assert "Programování v jazyce C" in header
    assert "PB071" in header
    assert "TLP" not in header
    assert "RESTRICTED" not in header
    assert "CONFIDENTIAL" not in header

    # Footer checks
    assert "Fakulta informatiky MU" in footer
    assert 'class="pageNumber"' in footer
    assert 'class="totalPages"' in footer
    assert "SHA-256" not in footer
    assert "abcdef12" not in footer


def test_academic_lecture_sample_compilation(tmp_path):
    """Verifies that the provided sample lecture note compiles cleanly with academic/lecture."""
    sample_file = Path(__file__).parent.parent / "examples" / "sample-lecture-fi-muni.md"
    assert sample_file.is_file(), f"Sample file not found at {sample_file}"

    out_file = tmp_path / "sample-lecture.html"
    config = PipelineConfig(
        input_file=sample_file,
        output_file=out_file,
        style="academic/lecture",
    )
    engine = ReportEngine(config)
    engine.run()

    html = out_file.read_text(encoding="utf-8")
    assert "Architektura moderních operačních systémů" in html
    assert "PV157 // Lecture 04" in html
    assert "callout-note" in html
    assert "callout-tip" in html
    assert "callout-warning" in html
    assert '<nav id="toc"' not in html


def test_academic_subthemes_resolution_and_inheritance():
    """Verifies that academic/modern, academic/classic, and academic/handbook resolve and inherit from academic/lecture."""
    resolver = ThemeResolver()

    for subtheme in ["academic/modern", "academic/classic", "academic/handbook"]:
        resolved = resolver.resolve(subtheme)
        assert resolved.name == subtheme
        assert "base" in resolved.inheritance_chain
        assert "academic/lecture" in resolved.inheritance_chain
        assert resolved.features.get("sticky_tables") is True
        assert len(resolved.stylesheet_paths) >= 2


def test_academic_sticky_tables_and_subthemes_compilation(tmp_path):
    """Verifies that sticky table headers and sub-theme CSS are compiled into output."""
    sample_md = """---
style: "academic/modern"
---

# Test Heading

1. First step
2. Second step

* Unordered item A
* Unordered item B

| Col 1 | Col 2 |
| :--- | :--- |
| Val A | Val B |
"""
    doc_path = tmp_path / "test_modern.md"
    doc_path.write_text(sample_md, encoding="utf-8")
    out_file = tmp_path / "test_modern.html"

    config = PipelineConfig(
        input_file=doc_path,
        output_file=out_file,
        style="academic/modern",
    )
    engine = ReportEngine(config)
    engine.run()

    html = out_file.read_text(encoding="utf-8")
    # Verify sticky table header rule
    assert "position: sticky" in html
    assert "top: 42px" in html
    # Verify modern list pill styling is present
    assert "counter(modern-counter)" in html
    # Verify pedagogical teacher-notes callout styles are present
    assert "details.teacher-notes" in html
    assert "background-color: #fffdf0" in html

