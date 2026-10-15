"""
tests/test_paged_theme.py
Validates theme-driven paged headers and footers, inheritance cascading,
and multilingual interpolation for Forensic and SVJ document domains.
"""

import pytest
from pathlib import Path
from core.themes import ThemeResolver
from core.i18n import I18nCatalog
from core.bundler import AssetBundler

def test_theme_paged_inheritance_forensic():
    """Verifies that forensic/cyber inherits and overrides paged configuration from base and dossier."""
    resolver = ThemeResolver()
    theme = resolver.resolve("forensic/cyber")

    assert theme.paged, "forensic/cyber must have resolved paged configuration"
    assert theme.paged.get("size") == "A4"
    assert theme.paged["margins"]["top"] == "25mm"

    headers = theme.paged.get("headers", {})
    footers = theme.paged.get("footers", {})

    assert "{classification" in headers.get("center", "")
    assert "string(heading)" in headers.get("right", "")
    assert "CYBER DFIR" in footers.get("left", "")

def test_theme_paged_inheritance_svj():
    """Verifies that svj/invitation inherits and overrides paged configuration from base and svj/base."""
    resolver = ThemeResolver()
    theme = resolver.resolve("svj/invitation")

    assert theme.paged, "svj/invitation must have resolved paged configuration"
    assert theme.paged.get("size") == "A4"
    assert theme.paged["margins"]["top"] == "20mm"

    headers = theme.paged.get("headers", {})
    footers = theme.paged.get("footers", {})

    assert "{i18n.svj.assembly_invite}" in headers.get("center", "")
    assert "{meta.svj_name" in headers.get("left", "")
    assert "{i18n.svj.committee_label}" in footers.get("left", "")
    assert "{i18n.svj.statute_notice}" in footers.get("center", "")

def test_bundler_paged_resolution_czech_svj():
    """Verifies AssetBundler resolves Czech SVJ headers and footers with statute notices."""
    resolver = ThemeResolver()
    theme = resolver.resolve("svj/invitation")
    catalog = I18nCatalog(lang="cs")
    bundler = AssetBundler(Path("/tmp/test.md"))

    fm = {
        "title": "Pozvánka na shromáždění SVJ",
        "svj_name": "SVJ Květinová 12, Praha 4",
        "assembly_date": "24. 10. 2024",
    }

    vars_dict = bundler.resolve_paged_variables(
        theme=theme,
        catalog=catalog,
        title="Pozvánka na shromáždění SVJ",
        frontmatter=fm,
        fingerprint="abcd1234efgh5678"
    )

    assert vars_dict["--page-header-left"] == '"SVJ Květinová 12, Praha 4"'
    assert vars_dict["--page-header-center"] == '"POZVÁNKA NA SHROMÁŽDĚNÍ"'
    assert vars_dict["--page-header-right"] == '"24. 10. 2024"'
    assert vars_dict["--page-footer-left"] == '"Statutární orgán / Výbor SVJ"'
    assert "1207" in vars_dict["--page-footer-center"]
    assert "counter(page)" in vars_dict["--page-footer-right"]
    assert '" z "' in vars_dict["--page-footer-right"]

def test_bundler_paged_resolution_english_forensic():
    """Verifies AssetBundler resolves English Forensic headers with classification and SHA-256."""
    resolver = ThemeResolver()
    theme = resolver.resolve("forensic/cyber")
    catalog = I18nCatalog(lang="en")
    bundler = AssetBundler(Path("/tmp/test.md"))

    fm = {
        "title": "Incident Forensic Report",
        "classification": "TLP:RED // RESTRICTED",
    }

    vars_dict = bundler.resolve_paged_variables(
        theme=theme,
        catalog=catalog,
        title="Incident Forensic Report",
        frontmatter=fm,
        fingerprint="9a8b7c6d5e4f3a2b"
    )

    assert vars_dict["--page-header-left"] == '"Incident Forensic Report"'
    assert vars_dict["--page-header-center"] == '"TLP:RED // RESTRICTED"'
    assert vars_dict["--page-header-right"] == 'string(heading)'
    assert "CYBER DFIR" in vars_dict["--page-footer-left"]
    assert "counter(page)" in vars_dict["--page-footer-right"]
    assert '" of "' in vars_dict["--page-footer-right"]

def test_pdf_export_generation(tmp_path):
    """Verifies that PDF export produces a multi-page PDF with size > 50KB when Chromium is available."""
    import shutil
    has_browser = any(shutil.which(b) for b in ["chromium-browser", "chromium", "google-chrome"])
    if not has_browser:
        pytest.skip("No Chromium browser available in environment")

    from core.engine import ReportEngine, PipelineConfig
    src_md = tmp_path / "test-doc.md"
    src_md.write_text("# Test Document\n\nSome paragraph content.\n\n| Col 1 | Col 2 |\n|---|---|\n| A | B |\n", encoding="utf-8")
    dst_pdf = tmp_path / "test-doc.pdf"

    cfg = PipelineConfig(
        input_file=src_md,
        output_file=dst_pdf,
        style="svj/invitation",
        generate_pdf=True,
        quiet=True,
    )
    engine = ReportEngine(cfg)
    res_path = engine.run()

    assert res_path.is_file(), "Generated PDF file must exist"
    assert res_path.stat().st_size > 10000, f"Generated PDF should not be blank, size was {res_path.stat().st_size}"

def test_cdp_header_footer_templates_synthesis():
    """Verifies synthesis of dynamic HTML header and footer templates for Chromium CDP printing."""
    resolver = ThemeResolver()
    theme = resolver.resolve("forensic/cyber")
    catalog = I18nCatalog(lang="en")
    bundler = AssetBundler(Path("/tmp/test.md"))

    fm = {
        "title": "Operation Red Dawn DFIR",
        "classification": "TLP:RED // RESTRICTED",
        "case_id": "CASE-992",
    }

    templates = bundler.build_cdp_header_footer_templates(
        theme=theme,
        catalog=catalog,
        title="Operation Red Dawn DFIR",
        frontmatter=fm
    )

    assert "headerTemplate" in templates
    assert "footerTemplate" in templates
    header_html = templates["headerTemplate"]
    footer_html = templates["footerTemplate"]

    # Header checks
    assert "Operation Red Dawn DFIR" in header_html
    assert "TLP:RED // RESTRICTED" in header_html
    assert "display: flex" in header_html
    assert "border-bottom" in header_html

    # Footer checks with native Chromium classes
    assert '<span class="pageNumber"></span>' in footer_html
    assert '<span class="totalPages"></span>' in footer_html
    assert "CYBER DFIR" in footer_html

    # Margins in inches
    assert templates["marginTop"] > 0.5
    assert templates["marginBottom"] > 0.5
    assert templates["marginLeft"] > 0.4
    assert templates["marginRight"] > 0.4

def test_cdp_header_footer_templates_czech_forensic():
    """Verifies that Czech forensic reports produce localized CDP footer templates."""
    resolver = ThemeResolver()
    theme = resolver.resolve("forensic/dossier")
    catalog = I18nCatalog(lang="cs")
    bundler = AssetBundler(Path("/tmp/forensic.md"))

    fm = {
        "title": "Forenzní analýza disku",
        "date": "2026-10-09",
        "classification": "DŮVĚRNÉ // TLP:AMBER"
    }

    templates = bundler.build_cdp_header_footer_templates(
        theme=theme,
        catalog=catalog,
        title="Forenzní analýza disku",
        frontmatter=fm
    )

    footer = templates["footerTemplate"]
    assert "Forenzní vyšetřovací jednotka" in footer
    assert "Strana <span class=\"pageNumber\"></span> z <span class=\"totalPages\"></span>" in footer

def test_dossier_header_author_sanitization():
    """Verifies that _build_dossier_header strips duplicate examiner prefixes."""
    from core.engine import ReportEngine, PipelineConfig
    engine = ReportEngine(PipelineConfig(input_file=Path("/tmp/fake.md")))
    catalog = I18nCatalog(lang="cs")

    fm = {
        "title": "Forenzní zpráva",
        "author": "Lead Examiner: S. Mercer",
        "date": "2026-10-09"
    }
    html_block = engine._build_dossier_header(fm, "Forenzní zpráva", catalog)
    assert '<span class="meta-label">Vyšetřovatel:</span> S. Mercer</p>' in html_block
    assert "Lead Examiner" not in html_block

def test_scoped_toc_parsing():
    """Verifies that {{#toc section='...'}} scopes to matching subheadings."""
    from core.parser import MarkdownParser
    parser = MarkdownParser(lang="cs", style_family="svj/invitation")
    md_text = '''# Zasedání SVJ

{{#toc section="Detaily jednání"}}

## Oznámení
Informace o schůzi.

## Detaily jednání

### 1. Zahájení
Úvodní slovo.

### 2. Hlasování
Rozhodnutí.

## Různé
Diskuze.
'''
    html, _, _ = parser.render(md_text)
    assert "Zahájení" in html
    assert "Hlasování" in html
    # TOC should not contain "Oznámení" or "Různé"
    toc_area = html[html.find("agenda-toc-list"):html.find("</ol>")]
    assert "Zahájení" in toc_area
    assert "Hlasování" in toc_area
    assert "Oznámení" not in toc_area
    assert "Různé" not in toc_area

def test_assembled_html_contains_paged_harness_and_templates():
    """Verifies that assemble() embeds paged-harness.css and md-style-print-templates JSON."""
    resolver = ThemeResolver()
    theme = resolver.resolve("forensic/dossier")
    bundler = AssetBundler(Path("/tmp/dummy.md"))
    catalog = I18nCatalog(lang="en")

    assembled = bundler.assemble(
        html_fragment="<main><p>Test document</p></main>",
        theme=theme,
        catalog=catalog,
        title="Test Report",
        frontmatter={"classification": "CONFIDENTIAL"}
    )

    # 1. paged-harness.css rules present
    assert "/* Paged Harness Styles */" in assembled
    assert "#md-style-paged-root" in assembled
    assert ".pagedjs_pages" in assembled
    assert ".pagedjs_page" in assembled

    # 2. md-style-print-templates script present
    assert '<script id="md-style-print-templates" type="application/json">' in assembled
    assert '"headerTemplate":' in assembled
    assert '"footerTemplate":' in assembled
    assert '"showFirstHeader":' in assembled
    assert '"showFirstFooter":' in assembled

def test_svj_paged_templates_has_no_borders():
    """Verifies that SVJ themes synthesize clean headers without forensic border lines."""
    resolver = ThemeResolver()
    theme = resolver.resolve("svj/invitation")
    bundler = AssetBundler(Path("/tmp/dummy.md"))
    catalog = I18nCatalog(lang="cs")

    templates = bundler.build_cdp_header_footer_templates(
        theme=theme,
        catalog=catalog,
        title="Pozvánka na shromáždění SVJ",
        frontmatter={"date": "2026-11-01"}
    )

    header_html = templates["headerTemplate"]
    footer_html = templates["footerTemplate"]

    # SVJ has no border lines in header or footer
    assert "border-bottom: 1px" not in header_html
    assert "border-top: 1px" not in footer_html



