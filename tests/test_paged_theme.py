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
