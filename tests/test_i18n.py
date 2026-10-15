"""
tests/test_i18n.py
Unit tests for I18nCatalog and localized translations.
"""

from core.i18n import I18nCatalog

def test_i18n_catalog_czech_and_english():
    cat_cs = I18nCatalog("cs")
    cat_en = I18nCatalog("en")

    assert cat_cs.t("callouts.note") == "POZNÁMKA"
    assert cat_en.t("callouts.note") == "NOTE"

    assert cat_cs.t("callouts.warning") == "VAROVÁNÍ"
    assert cat_en.t("callouts.warning") == "WARNING"

    assert cat_cs.t("badges.statute") == "ZÁKONNÉ USTANOVENÍ"
    assert cat_en.t("badges.statute") == "LEGAL STATUTE"

def test_i18n_fallback_to_english():
    # If a key only exists in en.json, cs catalog falls back to en
    cat_cs = I18nCatalog("cs")
    # Non-existent key falls back to default or uppercase key
    assert cat_cs.t("non.existent.key", default="DEFAULT") == "DEFAULT"

def test_i18n_export_ui_dict():
    cat = I18nCatalog("cs")
    ui = cat.export_ui_dict()
    assert "filter_placeholder" in ui
    assert "copy" in ui
    assert ui["copy"] == "Kopírovat"
    # Also verify flattened key exists
    assert "ui.copy" in ui
    assert ui["ui.copy"] == "Kopírovat"

def test_i18n_custom_file_and_frontmatter_overrides(tmp_path):
    custom_json = tmp_path / "custom_i18n.json"
    custom_json.write_text('{"callouts": {"note": "POZNÁMEČKA"}, "custom_sec": {"key": "val"}}', encoding="utf-8")

    fm = {
        "i18n": {
            "callouts": {"warning": "POZOR VÝSTRAHA"}
        }
    }

    cat = I18nCatalog("cs", custom_file=custom_json, frontmatter=fm)
    assert cat.t("callouts.note") == "POZNÁMEČKA"
    assert cat.t("callouts.warning") == "POZOR VÝSTRAHA"
    assert cat.t("custom_sec.key") == "val"
    # Unoverridden remains standard
    assert cat.t("callouts.info") == "INFORMACE"

def test_i18n_export_css_variables():
    cat = I18nCatalog("cs")
    vars_map = cat.export_css_variables()
    assert "--i18n-examiner" in vars_map
    assert "--i18n-date" in vars_map
    assert "--i18n-report-title" in vars_map
    assert vars_map["--i18n-examiner"] == '"Vyšetřovatel:"'

