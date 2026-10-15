"""
tests/test_frontmatter_and_viewer_control.py
Tests for namespaced frontmatter configuration (`md-style:` / `md_style:`)
and CLI / frontmatter viewer toggle controls (`--viewer`, `--no-viewer`, `--no-interactive`).
"""

from pathlib import Path
import pytest

from core.frontmatter import normalize_frontmatter, get_frontmatter_option
from core.cli import build_parser
from core.engine import ReportEngine, PipelineConfig


def test_normalize_frontmatter_namespaces():
    # 1. Namespaced under md-style
    raw_1 = {
        "title": "Incident Dossier",
        "tags": ["obsidian", "tag"],
        "md-style": {
            "style": "forensic/cyber",
            "viewer": False,
            "dossier_header": True,
            "report_badge": "CONFIDENTIAL"
        }
    }
    norm_1 = normalize_frontmatter(raw_1)
    assert norm_1["title"] == "Incident Dossier"
    assert norm_1["tags"] == ["obsidian", "tag"]
    assert norm_1["style"] == "forensic/cyber"
    assert norm_1["theme"] == "forensic/cyber"
    assert norm_1["viewer"] is False
    assert norm_1["interactive_viewer"] is False
    assert norm_1["dossier_header"] is True
    assert norm_1["report_badge"] == "CONFIDENTIAL"
    assert "md-style" in norm_1

    # 2. Namespaced under md_style
    raw_2 = {
        "title": "Notice",
        "md_style": {
            "theme": "svj/invitation",
            "viewer": True,
        }
    }
    norm_2 = normalize_frontmatter(raw_2)
    assert norm_2["style"] == "svj/invitation"
    assert norm_2["theme"] == "svj/invitation"
    assert norm_2["interactive_viewer"] is True
    assert norm_2["viewer"] is True

    # 3. Namespace takes precedence over root
    raw_3 = {
        "style": "forensic",
        "viewer": True,
        "md-style": {
            "style": "forensic/cyber",
            "viewer": False
        }
    }
    norm_3 = normalize_frontmatter(raw_3)
    assert norm_3["style"] == "forensic/cyber"
    assert norm_3["viewer"] is False
    assert norm_3["interactive_viewer"] is False


def test_normalize_frontmatter_string_booleans():
    cases = [
        ("false", False),
        ("False", False),
        ("no", False),
        ("off", False),
        ("0", False),
        ("disable", False),
        ("disabled", False),
        ("true", True),
        ("True", True),
        ("yes", True),
        ("on", True),
        ("1", True),
    ]
    for str_val, expected in cases:
        norm = normalize_frontmatter({"md-style": {"viewer": str_val}})
        assert norm["interactive_viewer"] is expected, f"Failed for {str_val}"
        assert norm["viewer"] is expected, f"Failed for {str_val}"


def test_get_frontmatter_option():
    fm = {
        "title": "Doc",
        "md-style": {
            "report_badge": "TOP SECRET"
        }
    }
    assert get_frontmatter_option(fm, "report_badge") == "TOP SECRET"
    assert get_frontmatter_option(fm, "title") == "Doc"
    assert get_frontmatter_option(fm, "non_existent", default="fallback") == "fallback"


def test_cli_viewer_flags(tmp_path):
    parser = build_parser()
    dummy_doc = str(tmp_path / "report.md")

    # Default: None (cascades to frontmatter / theme)
    args_default = parser.parse_args([dummy_doc])
    assert args_default.interactive_viewer is None

    # Explicit --no-viewer
    args_no_viewer = parser.parse_args([dummy_doc, "--no-viewer"])
    assert args_no_viewer.interactive_viewer is False

    # Explicit --no-interactive
    args_no_interactive = parser.parse_args([dummy_doc, "--no-interactive"])
    assert args_no_interactive.interactive_viewer is False

    # Explicit --viewer
    args_viewer = parser.parse_args([dummy_doc, "--viewer"])
    assert args_viewer.interactive_viewer is True


def test_compilation_with_namespaced_frontmatter_disabled_viewer(tmp_path):
    doc_path = tmp_path / "doc_namespaced_no_viewer.md"
    doc_path.write_text(
        "---\n"
        "title: Static Security Report\n"
        "tags: [cve, audit]\n"
        "md-style:\n"
        "  style: forensic/cyber\n"
        "  viewer: false\n"
        "---\n"
        "# Executive Summary\n\n"
        "This is an offline static document without Svelte interactive overhead.\n"
    )
    out_html = tmp_path / "output_static.html"

    cfg = PipelineConfig(
        input_file=doc_path,
        output_file=out_html,
        allow_online=False,
        quiet=True
    )
    engine = ReportEngine(cfg)
    result = engine.run()

    content = result.read_text(encoding="utf-8")

    # Verify theme was resolved from md-style namespace
    assert "theme-forensic-cyber" in content

    # Verify Svelte viewer was completely omitted
    assert "id=\"md-style-viewer-root\"" not in content
    assert "/* Svelte Viewer Component Styles */" not in content
    assert "MdStyleViewer.initViewer" not in content

    # Verify document content itself is present
    assert "Executive Summary" in content
    assert "This is an offline static document" in content


def test_cli_override_enables_and_disables_viewer(tmp_path):
    # Document with viewer disabled in frontmatter
    doc_path = tmp_path / "doc_override.md"
    doc_path.write_text(
        "---\n"
        "title: Overridden Report\n"
        "md-style:\n"
        "  viewer: false\n"
        "---\n"
        "# Content\n\nSome text.\n"
    )

    # 1. CLI passes interactive_viewer=True (--viewer): should override frontmatter!
    out_html_enabled = tmp_path / "out_enabled.html"
    cfg_enabled = PipelineConfig(
        input_file=doc_path,
        output_file=out_html_enabled,
        interactive_viewer=True,
        allow_online=False,
        quiet=True
    )
    engine_enabled = ReportEngine(cfg_enabled)
    engine_enabled.run()
    content_enabled = out_html_enabled.read_text(encoding="utf-8")
    assert "id=\"md-style-viewer-root\"" in content_enabled
    assert "MdStyleViewer.initViewer" in content_enabled

    # 2. Document with viewer enabled by default, CLI passes interactive_viewer=False (--no-viewer)
    doc_default_path = tmp_path / "doc_default.md"
    doc_default_path.write_text(
        "---\n"
        "title: Default Report\n"
        "---\n"
        "# Content\n\nSome text.\n"
    )
    out_html_disabled = tmp_path / "out_disabled.html"
    cfg_disabled = PipelineConfig(
        input_file=doc_default_path,
        output_file=out_html_disabled,
        interactive_viewer=False,
        allow_online=False,
        quiet=True
    )
    engine_disabled = ReportEngine(cfg_disabled)
    engine_disabled.run()
    content_disabled = out_html_disabled.read_text(encoding="utf-8")
    assert "id=\"md-style-viewer-root\"" not in content_disabled
    assert "MdStyleViewer.initViewer" not in content_disabled
