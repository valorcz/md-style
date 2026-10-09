"""
tests/test_themes.py
Unit tests for ThemeResolver and declarative theme inheritance.
"""

from core.themes import ThemeResolver

def test_theme_inheritance_chain():
    resolver = ThemeResolver()
    theme = resolver.resolve("forensic/cyber")

    assert theme.name == "forensic/cyber"
    assert theme.inheritance_chain == ["base", "forensic/cyber"]
    sheet_names = [s.name for s in theme.stylesheet_paths]
    assert "base.css" in sheet_names
    assert "dossier-header.css" in sheet_names
    assert "cyber.css" in sheet_names

def test_theme_variable_overrides():
    resolver = ThemeResolver()
    theme = resolver.resolve("forensic/cyber")

    assert theme.variables.get("--bg-primary") == "#070b12"
    assert theme.variables.get("--accent-cyan") == "#06b6d4"

def test_theme_fallback():
    resolver = ThemeResolver()
    theme = resolver.resolve("non_existent_style")

    assert theme.name == "base"
    assert theme.inheritance_chain == ["base"]
