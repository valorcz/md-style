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


def test_frontmatter_style_cascade(tmp_path):
    """Verifies that frontmatter style is honored when CLI style is None, and CLI overrides if specified."""
    from core.engine import ReportEngine, PipelineConfig

    # 1. Document with frontmatter style: forensic-cyber
    cyber_doc = tmp_path / "test_cyber.md"
    cyber_doc.write_text(
        "---\ntitle: Cyber Report\nstyle: forensic-cyber\n---\n\n# Header\nContent\n",
        encoding="utf-8"
    )

    # When CLI style is None (default behavior when -s not passed)
    cfg1 = PipelineConfig(input_file=cyber_doc, style=None, quiet=True)
    engine1 = ReportEngine(cfg1)
    # Read and parse frontmatter to check resolved style
    with open(cyber_doc, "r", encoding="utf-8") as f:
        _, fm1 = engine1._normalize_nested_containers(f.read()), {}
    from core.parser import MarkdownParser
    _, fm1 = MarkdownParser().parse_frontmatter(cyber_doc.read_text(encoding="utf-8"))
    resolved_style1 = cfg1.style or fm1.get("style") or "forensic"
    theme1 = engine1.theme_resolver.resolve(resolved_style1)
    assert theme1.name == "forensic/cyber"

    # When CLI style is explicitly specified, it overrides frontmatter
    cfg2 = PipelineConfig(input_file=cyber_doc, style="svj/invitation", quiet=True)
    engine2 = ReportEngine(cfg2)
    resolved_style2 = cfg2.style or fm1.get("style") or "forensic"
    theme2 = engine2.theme_resolver.resolve(resolved_style2)
    assert theme2.name == "svj/invitation"

    # 2. Document without frontmatter style falls back to forensic (dossier)
    dossier_doc = tmp_path / "test_dossier.md"
    dossier_doc.write_text(
        "---\ntitle: Dossier Report\n---\n\n# Header\nContent\n",
        encoding="utf-8"
    )
    cfg3 = PipelineConfig(input_file=dossier_doc, style=None, quiet=True)
    engine3 = ReportEngine(cfg3)
    _, fm3 = MarkdownParser().parse_frontmatter(dossier_doc.read_text(encoding="utf-8"))
    resolved_style3 = cfg3.style or fm3.get("style") or "forensic"
    theme3 = engine3.theme_resolver.resolve(resolved_style3)
    assert theme3.name == "forensic/dossier"

