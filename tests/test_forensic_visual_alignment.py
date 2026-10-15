"""
tests/test_forensic_visual_alignment.py
Regression tests ensuring visual style, typography, and AST transformations
remain consistent with the original md-style (forensic dossier).
"""

from pathlib import Path
from core.engine import ReportEngine, PipelineConfig
from core.parser import MarkdownParser
from core.themes import ThemeResolver

def test_default_theme_is_forensic():
    resolver = ThemeResolver()
    theme = resolver.resolve("forensic")
    assert theme.name == "forensic/dossier"

    # Engine without explicit style defaults to forensic/dossier
    cfg = PipelineConfig(input_file=Path("examples/sample-forensic-report.md"))
    engine = ReportEngine(cfg)
    resolved = engine.theme_resolver.resolve(cfg.style or "forensic")
    assert resolved.name == "forensic/dossier"

def test_kpi_grid_card_transformation():
    parser = MarkdownParser()
    md = """
::: {.kpi-grid}
- **Compromised Asset:** `DC-CORP-01` (Primary Domain Controller)
- **Threat Actor:** UNC-2026 / ZAWOOO Affiliate
- **Initial Vector:** Exploitation of exposed RPC service (`T1190`)
:::
"""
    html_out, _, _ = parser.render(md)
    assert '<div class="kpi-grid">' in html_out
    assert '<div class="kpi-card">' in html_out
    assert '<div class="kpi-label">Compromised Asset</div>' in html_out
    assert '<div class="kpi-value">' in html_out
    assert '<code>DC-CORP-01</code>' in html_out
    assert '<div class="kpi-label">Threat Actor</div>' in html_out
    assert '<div class="kpi-label">Initial Vector</div>' in html_out

def test_timeline_table_detection():
    parser = MarkdownParser()
    md = """
## 3. Incident Timeline & Forensic Reconstruction

| Timestamp (UTC) | Event | Observation |
|---|---|---|
| `2026-09-11 02:14:22` | Breach | Inbound exploit |
| `2026-09-11 02:14:58` | PrivEsc | Process spawned |
"""
    html_out, _, _ = parser.render(md)
    assert '<table class="table-timeline">' in html_out or 'table-timeline' in html_out

def test_blockquote_lead_badge_preservation():
    parser = MarkdownParser()
    md = """
> **CRITICAL FINDING**: An unauthenticated attacker executed arbitrary commands via a weaponized RPC vulnerability.

> **EVIDENCE VERIFICATION**: All disk image hashes matched pre- and post-acquisition checks.
"""
    html_out, _, _ = parser.render(md)
    # Must remain standard blockquotes so forensic.css blockquote strong:first-child styles them
    assert '<blockquote>' in html_out
    assert '<strong>CRITICAL FINDING</strong>' in html_out
    assert '<strong>EVIDENCE VERIFICATION</strong>' in html_out
    # Must NOT be hijacked into callout alert boxes
    assert 'callout-critical' not in html_out
    assert 'callout-evidence' not in html_out

def test_dossier_header_typography_css():
    css_path = Path("styles/forensic/components/dossier-header.css")
    assert css_path.is_file()
    content = css_path.read_text(encoding="utf-8")
    assert "h1.title::after" in content
    assert "display: none !important" in content
