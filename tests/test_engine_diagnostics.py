"""
tests/test_engine_diagnostics.py
Verification tests for PipelineConfig defaults, stage timing metrics, and CLI exit codes.
"""

import sys
import subprocess
from pathlib import Path
import pytest
from unittest.mock import patch

from core.engine import ReportEngine, PipelineConfig
from core.diagnostics import PipelineTimer


def test_pipeline_config_default_highlight_style_none(tmp_path):
    """Verifies that PipelineConfig defaults highlight_style to None and avoids Kate crash."""
    src = tmp_path / "code_doc.md"
    src.write_text("# Code Document\n\n```python\nprint(42)\n```\n", encoding="utf-8")
    dst = tmp_path / "code_doc.html"

    # 1. Check default dataclass attribute
    cfg = PipelineConfig(input_file=src, output_file=dst)
    assert cfg.highlight_style is None, "Default highlight_style must be None"

    # 2. Run engine with default config; must succeed without pygments ClassNotFound: kate
    engine = ReportEngine(cfg)
    out = engine.run()
    assert out.is_file(), "Generated HTML must exist"
    assert dst.is_file()

    # 3. Check explicit override
    cfg_override = PipelineConfig(input_file=src, output_file=dst, highlight_style="monokai")
    assert cfg_override.highlight_style == "monokai"


def test_stage_1_timer_accuracy(tmp_path):
    """Verifies that Stage 1 timer measures non-zero duration covering validation and ingestion."""
    src = tmp_path / "timer_doc.md"
    src.write_text("---\ntitle: Timer Test\n---\n# Content\nParagraph body text.\n", encoding="utf-8")
    dst = tmp_path / "timer_doc.html"

    cfg = PipelineConfig(input_file=src, output_file=dst, quiet=True)
    engine = ReportEngine(cfg)
    engine.run()

    timings = engine.get_stage_timings()
    assert "stage1" in timings
    assert "stage2" in timings
    assert "stage3" in timings
    assert "stage4" in timings
    assert "stage5" in timings
    assert "total" in timings

    # Stage 1 must be strictly positive (not a 0s empty block)
    assert timings["stage1"] > 0.0, f"Stage 1 duration was {timings['stage1']}, expected > 0.0"
    assert timings["total"] >= timings["stage1"], "Total duration must be >= stage 1 duration"


def test_pdf_export_failure_raises_runtime_error(tmp_path):
    """Verifies that _compile_pdf raises RuntimeError when no Chromium browser or printer script is available."""
    src = tmp_path / "pdf_test.md"
    src.write_text("# PDF Failure Test\nContent\n", encoding="utf-8")
    dst_pdf = tmp_path / "failing_report.pdf"

    cfg = PipelineConfig(
        input_file=src,
        output_file=dst_pdf,
        generate_pdf=True,
        quiet=True
    )
    engine = ReportEngine(cfg)

    with patch("shutil.which", return_value=None):
        with pytest.raises(RuntimeError, match="PDF export failed"):
            engine.run()

    # Temporary html must be cleaned up
    tmp_html = dst_pdf.with_suffix(".tmp.html")
    assert not tmp_html.exists(), "Intermediate .tmp.html must be unlinked"
    assert not dst_pdf.exists(), "Destination PDF must not exist on failure"


def test_cli_exits_code_1_on_pdf_failure(tmp_path):
    """Verifies that CLI exits with return code 1 when PDF compilation fails."""
    src = tmp_path / "cli_pdf.md"
    src.write_text("# PDF CLI Test\nContent\n", encoding="utf-8")
    dst_pdf = tmp_path / "cli_pdf.pdf"

    res = subprocess.run(
        [sys.executable, "-m", "core.cli", str(src), "-o", str(dst_pdf), "--pdf"],
        env={"PATH": "/nonexistent", "HOME": str(tmp_path)},
        capture_output=True,
        text=True
    )

    assert res.returncode == 1, f"Expected returncode 1, got {res.returncode}. Output: {res.stderr}"
    assert "Compilation failed:" in res.stderr or "PDF export failed" in res.stderr
    assert not dst_pdf.is_file(), "PDF must not be generated"


def test_verbose_timing_breakdown_output(tmp_path, capsys):
    """Verifies that verbose mode prints the structured 5-stage timing breakdown."""
    src = tmp_path / "verbose_doc.md"
    src.write_text("# Verbose Doc\nBody paragraph.\n", encoding="utf-8")
    dst = tmp_path / "verbose_doc.html"

    cfg = PipelineConfig(input_file=src, output_file=dst, verbose=True, quiet=False)
    engine = ReportEngine(cfg)
    engine.run()

    captured = capsys.readouterr()
    err_text = captured.err

    assert "Pipeline Timing Breakdown:" in err_text
    assert "Stage 1 (Validation & Ingestion):" in err_text
    assert "Stage 2 (Knowledge Pack Sync):" in err_text
    assert "Stage 3 (Theme Resolution):" in err_text
    assert "Stage 4 (Markdown AST & Transforms):" in err_text
    assert "Stage 5 (Output Bundling & Export):" in err_text
    assert "Total Compilation Time:" in err_text


def test_quiet_mode_suppresses_timing_diagnostics(tmp_path, capsys):
    """Verifies that quiet mode suppresses timing breakdown and success banner."""
    src = tmp_path / "quiet_doc.md"
    src.write_text("# Quiet Doc\nBody paragraph.\n", encoding="utf-8")
    dst = tmp_path / "quiet_doc.html"

    cfg = PipelineConfig(input_file=src, output_file=dst, quiet=True)
    engine = ReportEngine(cfg)
    engine.run()

    captured = capsys.readouterr()
    assert "Pipeline Timing Breakdown:" not in captured.err
    assert "Report generated:" not in captured.err


def test_cli_exit_codes_matrix(tmp_path):
    """Verifies exit code behavior across success, missing file, and disallowed file types."""
    # 1. Missing input file -> exit code 1
    res_missing = subprocess.run(
        [sys.executable, "-m", "core.cli", str(tmp_path / "nonexistent.md")],
        capture_output=True,
        text=True
    )
    assert res_missing.returncode == 1

    # 2. Disallowed binary format -> exit code 1
    fake_pdf = tmp_path / "invalid.pdf"
    fake_pdf.write_bytes(b"%PDF-1.4\nSome binary content\n")
    res_invalid = subprocess.run(
        [sys.executable, "-m", "core.cli", str(fake_pdf)],
        capture_output=True,
        text=True
    )
    assert res_invalid.returncode == 1

    # 3. Valid markdown input -> exit code 0
    valid_md = tmp_path / "valid.md"
    valid_md.write_text("# Valid\nText\n", encoding="utf-8")
    valid_html = tmp_path / "valid.html"
    res_valid = subprocess.run(
        [sys.executable, "-m", "core.cli", str(valid_md), "-o", str(valid_html)],
        capture_output=True,
        text=True
    )
    assert res_valid.returncode == 0
    assert valid_html.is_file()
