"""
tests/test_theme_tools.py
Unit and integration tests for ThemeInspector, ThemeLinter, ThemeScaffolder,
and their CLI entrypoints.
"""

import sys
import shutil
import tempfile
from pathlib import Path
from rich.console import Console

import pytest

from core.themes import ThemeResolver
from core.theme_tool import (
    ThemeInspector,
    ThemeLinter,
    ThemeScaffolder,
    print_lint_report,
)
from core.config import STYLES_DIR


def test_theme_inspector_resolution_and_provenance():
    inspector = ThemeInspector()
    resolved = inspector.resolver.resolve("forensic/cyber")

    assert resolved.name == "forensic/cyber"
    assert resolved.inheritance_chain == ["base", "forensic/cyber"]
    assert len(resolved.stylesheet_paths) >= 4

    # Verify CSS custom properties provenance tracking
    assert resolved.variables.get("--bg-primary") == "#070b12"
    assert resolved.variable_sources.get("--bg-primary") == "forensic/cyber"
    assert resolved.variable_sources.get("--font-mono") == "base"
    assert resolved.variable_sources.get("--font-sans") == "base"

    # Verify Feature provenance tracking
    assert resolved.features.get("interactive_viewer") is True
    assert resolved.feature_sources.get("interactive_viewer") == "forensic/cyber"
    assert resolved.feature_sources.get("callouts") == "base"

    # Verify multi-tier inheritance (svj/invitation)
    svj_resolved = inspector.resolver.resolve("svj/invitation")
    assert svj_resolved.inheritance_chain == ["base", "svj/base", "svj/invitation"]
    assert svj_resolved.variable_sources.get("--accent") == "svj/base"
    assert svj_resolved.feature_sources.get("legal_inspector") == "svj/base"
    assert svj_resolved.feature_sources.get("break_ranges") == "svj/invitation"


def test_theme_inspector_render_dashboard():
    inspector = ThemeInspector()
    console = Console(record=True, width=120)

    # Inspect specific theme
    inspector.inspect_theme("forensic/cyber", console=console)
    output = console.export_text()

    assert "Theme Dossier — forensic/cyber" in output
    assert "Cascading Stylesheet Order" in output
    assert "Feature Flags & Capabilities" in output
    assert "Resolved CSS Custom Properties" in output
    assert "Paged.js Print & Margin Specification" in output
    assert "--bg-primary" in output

    # Inspect all themes summary
    console2 = Console(record=True, width=120)
    inspector.list_themes(console=console2)
    summary_output = console2.export_text()
    assert "Available md-style Themes & Print Styles" in summary_output
    assert "forensic/cyber" in summary_output
    assert "svj/invitation" in summary_output
    assert "base" in summary_output


def test_theme_linter_builtin_themes_zero_errors():
    """All built-in themes in styles/ must pass audit with 0 errors."""
    linter = ThemeLinter(STYLES_DIR)
    messages = linter.lint_all()

    errors = [m for m in messages if m.severity == "ERROR"]
    assert len(errors) == 0, f"Built-in themes contain errors: {errors}"


def test_theme_linter_targeted_clean_theme():
    linter = ThemeLinter(STYLES_DIR)
    messages = linter.lint_theme_name("forensic/cyber")
    errors = [m for m in messages if m.severity == "ERROR"]
    assert len(errors) == 0


def test_theme_linter_rules_detection(tmp_path):
    """Verifies that each lint rule detects intentional defects."""
    # 1. Broken YAML
    broken_yaml_dir = tmp_path / "broken_yaml"
    broken_yaml_dir.mkdir()
    (broken_yaml_dir / "theme.yaml").write_text("name: broken\n  invalid: [yaml", encoding="utf-8")

    linter = ThemeLinter(tmp_path)
    msgs = linter.lint_theme_file(broken_yaml_dir / "theme.yaml")
    rule_ids = {m.rule_id for m in msgs}
    assert "manifest/yaml-syntax" in rule_ids

    # 2. Missing required fields
    missing_dir = tmp_path / "missing_fields"
    missing_dir.mkdir()
    (missing_dir / "theme.yaml").write_text("stylesheets: []\n", encoding="utf-8")
    msgs = linter.lint_theme_file(missing_dir / "theme.yaml")
    rule_ids = {m.rule_id for m in msgs}
    assert "manifest/required-fields" in rule_ids

    # 3. Missing referenced stylesheet
    missing_css_dir = tmp_path / "missing_css"
    missing_css_dir.mkdir()
    (missing_css_dir / "theme.yaml").write_text(
        "name: missing_css\ntitle: Missing CSS Theme\nstylesheets:\n  - does_not_exist.css\n",
        encoding="utf-8"
    )
    msgs = linter.lint_theme_file(missing_css_dir / "theme.yaml")
    rule_ids = {m.rule_id for m in msgs}
    assert "assets/stylesheet-exists" in rule_ids

    # 4. Empty stylesheet (0 bytes)
    empty_css_dir = tmp_path / "empty_css"
    empty_css_dir.mkdir()
    (empty_css_dir / "empty.css").write_text("", encoding="utf-8")
    (empty_css_dir / "theme.yaml").write_text(
        "name: empty_css\ntitle: Empty CSS Theme\nstylesheets:\n  - empty.css\n",
        encoding="utf-8"
    )
    msgs = linter.lint_theme_file(empty_css_dir / "theme.yaml")
    rule_ids = {m.rule_id for m in msgs}
    assert "assets/non-empty" in rule_ids

    # 5. Invalid Paged.js paper orientation & margin units & template syntax
    paged_bad_dir = tmp_path / "paged_bad"
    paged_bad_dir.mkdir()
    (paged_bad_dir / "valid.css").write_text("body { margin: 0; }", encoding="utf-8")
    (paged_bad_dir / "theme.yaml").write_text(
        """name: paged_bad
title: Paged Bad Theme
stylesheets:
  - valid.css
paged:
  orientation: diagonal
  margins:
    top: 20badunit
  headers:
    left: "{doc_title"
  first_page:
    show_header: "yes"
""",
        encoding="utf-8"
    )
    msgs = linter.lint_theme_file(paged_bad_dir / "theme.yaml")
    rule_ids = {m.rule_id for m in msgs}
    assert "paged/orientation" in rule_ids
    assert "paged/margins-format" in rule_ids
    assert "paged/template-syntax" in rule_ids
    assert "paged/first-page-booleans" in rule_ids

    # 6. CSS syntax errors: unbalanced comment and unbalanced braces
    css_bad_dir = tmp_path / "css_bad"
    css_bad_dir.mkdir()
    (css_bad_dir / "bad.css").write_text("/* unclosed comment\nbody { color: red; \n", encoding="utf-8")
    (css_bad_dir / "theme.yaml").write_text(
        "name: css_bad\ntitle: CSS Bad Theme\nstylesheets:\n  - bad.css\n",
        encoding="utf-8"
    )
    msgs = linter.lint_theme_file(css_bad_dir / "theme.yaml")
    rule_ids = {m.rule_id for m in msgs}
    assert "css/comment-balance" in rule_ids
    assert "css/brace-balance" in rule_ids

    # 7. Unknown feature key
    feat_bad_dir = tmp_path / "feat_bad"
    feat_bad_dir.mkdir()
    (feat_bad_dir / "theme.yaml").write_text(
        "name: feat_bad\ntitle: Bad Feature Theme\nstylesheets: []\nfeatures:\n  invented_feature_key: true\n",
        encoding="utf-8"
    )
    msgs = linter.lint_theme_file(feat_bad_dir / "theme.yaml")
    rule_ids = {m.rule_id for m in msgs}
    assert "features/valid-keys" in rule_ids


def test_theme_scaffolder_and_validation(tmp_path):
    """Verifies that scaffolding a new theme produces valid, compliant files."""
    scaffolder = ThemeScaffolder(styles_root=STYLES_DIR)
    created_dir = scaffolder.scaffold("custom/marketing", extends="base", output_root=tmp_path)

    assert created_dir.is_dir()
    yaml_file = created_dir / "theme.yaml"
    css_file = created_dir / "marketing.css"
    assert yaml_file.is_file()
    assert css_file.is_file()

    # Lint the newly scaffolded theme against the main STYLES_DIR (so base is resolvable)
    linter = ThemeLinter(styles_root=STYLES_DIR)
    messages = linter.lint_theme_file(yaml_file)
    errors = [m for m in messages if m.severity == "ERROR"]
    assert len(errors) == 0, f"Scaffolded theme had lint errors: {errors}"


def test_theme_cli_subcommands(monkeypatch, capsys):
    from core.cli import main

    # 1. md-style theme list
    monkeypatch.setattr(sys, "argv", ["md-style", "theme", "list"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0

    # 2. md-style theme inspect forensic/cyber
    monkeypatch.setattr(sys, "argv", ["md-style", "theme", "inspect", "forensic/cyber"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0

    # 3. md-style theme lint forensic/cyber
    monkeypatch.setattr(sys, "argv", ["md-style", "theme", "lint", "forensic/cyber"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0

    # 4. md-style --theme-inspect
    monkeypatch.setattr(sys, "argv", ["md-style", "--theme-inspect", "svj/invitation"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0

    # 5. md-style --theme-lint
    monkeypatch.setattr(sys, "argv", ["md-style", "--theme-lint", "svj/invitation"])
    with pytest.raises(SystemExit) as exc:
        main()
    assert exc.value.code == 0
