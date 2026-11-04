"""
tests/test_dynamic_components.py
Test suite for document-defined dynamic Svelte components.
Verifies compiler bridge, parser plugin, pipeline integration, and browser interactivity.
"""

import json
import pytest
from pathlib import Path

from core.bundler.svelte_compiler import SvelteComponentCompiler
from core.parser import MarkdownParser
from core.pipeline.context import PipelineConfig, PipelineContext
from core.pipeline.stages.ingestion import Stage1Ingestion
from core.pipeline.stages.knowledge import Stage2Knowledge
from core.pipeline.stages.theme import Stage3Theme
from core.pipeline.stages.compilation import Stage4Compilation
from core.pipeline.stages.export import Stage5Export


REPO_ROOT = Path(__file__).resolve().parent.parent
EXAMPLE_COMPONENT = REPO_ROOT / "examples" / "components" / "LogicalPhysicalMap.svelte"


def test_compiler_availability():
    compiler = SvelteComponentCompiler()
    assert compiler.is_available() is True


def test_compiler_compiles_svelte_component(tmp_path):
    compiler = SvelteComponentCompiler()
    defs = [{"name": "LogicalPhysicalMap", "path": str(EXAMPLE_COMPONENT)}]
    result = compiler.compile_components(defs)

    assert result.get("success") is True
    assert "LogicalPhysicalMap" in result.get("components", {})
    comp = result["components"]["LogicalPhysicalMap"]
    assert "js" in comp
    assert "MdStyleViewer" in comp["js"]
    assert "window.__MD_STYLE_COMPONENTS__" in comp["js"]
    assert len(result.get("aggregatedCss", "")) > 100


def test_components_parser_plugin():
    parser = MarkdownParser()
    md_content = """
# Test Document

```component LogicalPhysicalMap title="Address Mapping" #mmu-map
initialFilter: "procB"
```
"""
    html_out, toc, meta = parser.render(md_content)

    assert 'class="doc-component-mount"' in html_out
    assert 'data-component="LogicalPhysicalMap"' in html_out
    assert 'data-props="{&quot;initialFilter&quot;: &quot;procB&quot;}"' in html_out or 'data-props="{\\"initialFilter\\": \\"procB\\"}"' in html_out
    assert 'id="mmu-map"' in html_out
    assert "Address Mapping" in html_out

    assert "LogicalPhysicalMap" in parser.doc_components
    assert parser.doc_components["LogicalPhysicalMap"]["props"] == {"initialFilter": "procB"}


def test_full_pipeline_compiles_standalone_html(tmp_path):
    doc_path = tmp_path / "test-component-doc.md"
    out_html = tmp_path / "test-component-doc.html"

    doc_path.write_text("""---
title: "Interactive Systems Test"
style: "academic/modern"
---

# Architecture Section

```component LogicalPhysicalMap title="Hardware MMU"
initialFilter: "all"
```
""", encoding="utf-8")

    cfg = PipelineConfig(
        input_file=doc_path,
        output_file=out_html,
        style="academic/modern",
    )
    ctx = PipelineContext(config=cfg)
    ctx.target_html = out_html

    Stage1Ingestion().execute(ctx)
    Stage2Knowledge().execute(ctx)
    Stage3Theme().execute(ctx)
    Stage4Compilation().execute(ctx)
    Stage5Export().execute(ctx)

    assert out_html.is_file()
    html_text = out_html.read_text(encoding="utf-8")

    # Invariants verification
    assert 'name="doc-components" content="LogicalPhysicalMap"' in html_text
    assert 'id="md-style-components"' in html_text
    assert 'Content-Security-Policy' in html_text
    assert "connect-src 'none'" in html_text
    assert "logical-physical-map" in html_text


def test_playwright_component_interactivity(page, tmp_path):
    pytest.importorskip("playwright")

    doc_path = tmp_path / "test-playwright.md"
    out_html = tmp_path / "test-playwright.html"

    doc_path.write_text("""---
title: "Playwright Interactive Test"
style: "academic/modern"
---

```component LogicalPhysicalMap
initialFilter: "procA"
```

```mermaid
graph LR
    A[Start] --> B[Finish]
```
""", encoding="utf-8")

    cfg = PipelineConfig(
        input_file=doc_path,
        output_file=out_html,
        style="academic/modern",
    )
    ctx = PipelineContext(config=cfg)
    ctx.target_html = out_html

    Stage1Ingestion().execute(ctx)
    Stage2Knowledge().execute(ctx)
    Stage3Theme().execute(ctx)
    Stage4Compilation().execute(ctx)
    Stage5Export().execute(ctx)

    console_errors = []
    page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    page.on("pageerror", lambda err: console_errors.append(str(err)))

    page.goto(f"file://{out_html.resolve()}")
    page.wait_for_selector(".logical-physical-map", timeout=5000)

    # 1. Check HUD component pill badge
    hud_badge = page.wait_for_selector(".hud-pill-component", timeout=3000)
    text = hud_badge.inner_text()
    assert "Interactive" in text

    # 2. Check initial filter 'procA'
    proc_a = page.wait_for_selector('.flat-btn:has-text("Process A (Browser)")')
    assert proc_a.evaluate('el => el.classList.contains("active")') is True

    # 3. Click 'Process B' and verify state transition
    proc_b = page.wait_for_selector('.flat-btn:has-text("Process B (Editor)")')
    proc_b.click()
    page.wait_for_timeout(100)
    assert proc_b.evaluate('el => el.classList.contains("active")') is True
    assert proc_a.evaluate('el => el.classList.contains("active")') is False

    # 4. Press presenter hotkey '4' and verify Page Fault active
    page.keyboard.press("4")
    page.wait_for_timeout(100)
    fault_btn = page.wait_for_selector('.flat-btn:has-text("Page Fault")')
    assert fault_btn.evaluate('el => el.classList.contains("active")') is True

    # 5. Verify tailored toolbar on dynamic component figure (Option B)
    comp_fig = page.query_selector("figure.doc-component-container")
    assert comp_fig is not None
    comp_toolbar = comp_fig.query_selector(".figure-toolbar")
    assert comp_toolbar is not None

    # Components must have Fullscreen and Wide, but NOT Copy or Download
    assert comp_fig.query_selector('.fig-btn:has-text("Fullscreen")') is not None
    assert comp_fig.query_selector('.fig-btn:has-text("Wide")') is not None
    assert comp_fig.query_selector('.fig-btn:has-text("Copy")') is None
    assert comp_fig.query_selector('button[title*="Download"]') is None

    # Test Wide toggle on dynamic component
    wide_btn = comp_fig.query_selector('.fig-btn:has-text("Wide")')
    wide_btn.click(force=True)
    page.wait_for_timeout(100)
    assert comp_fig.evaluate('el => el.classList.contains("wide")') is True
    # Verify wide breakout card surface is grounded with background
    wide_bg = page.evaluate('el => window.getComputedStyle(el).backgroundColor', comp_fig)
    assert '255, 255, 255' in wide_bg

    # 6. Test Live Component Fullscreen Mode (Option A)
    fs_btn = comp_fig.query_selector('.fig-btn:has-text("Fullscreen")')
    assert fs_btn is not None
    fs_btn.click(force=True)
    page.wait_for_timeout(150)

    # In fullscreen: class attached to figure and body
    assert comp_fig.evaluate('el => el.classList.contains("component-fullscreen")') is True
    assert page.evaluate('() => document.body.classList.contains("has-component-fullscreen")') is True

    # Verify all component controls and status bar remain present and interactive
    assert comp_fig.query_selector(".map-toolbar").is_visible() is True
    assert comp_fig.query_selector(".map-svg").is_visible() is True
    assert comp_fig.query_selector(".map-status-bar").is_visible() is True

    # Test live interaction while in fullscreen (click Process A)
    proc_a_btn = comp_fig.query_selector('.flat-btn:has-text("Process A (Browser)")')
    proc_a_btn.click()
    page.wait_for_timeout(100)
    assert proc_a_btn.evaluate('el => el.classList.contains("active")') is True

    # Test Exit fullscreen via Esc key
    page.keyboard.press("Escape")
    page.wait_for_timeout(150)
    assert comp_fig.evaluate('el => el.classList.contains("component-fullscreen")') is False
    assert page.evaluate('() => document.body.classList.contains("has-component-fullscreen")') is False

    # 7. Verify standard static diagram retains Zoom/Lightbox, Copy, Download
    diag_fig = page.query_selector("figure.mermaid-diagram")
    assert diag_fig is not None
    diag_toolbar = diag_fig.query_selector(".figure-toolbar")
    assert diag_toolbar is not None

    # Static diagrams have Zoom, Wide, Copy, Download
    zoom_btn = diag_fig.query_selector('.fig-btn:has-text("Zoom")')
    assert zoom_btn is not None
    assert diag_fig.query_selector('.fig-btn:has-text("Copy")') is not None
    assert diag_fig.query_selector('button[title*="Download"]') is not None

    # Clicking Zoom opens the vector lightbox
    zoom_btn.click(force=True)
    page.wait_for_timeout(200)
    lightbox = page.query_selector(".lightbox-backdrop")
    assert lightbox is not None
    assert lightbox.query_selector("svg") is not None
    modal = page.query_selector(".lightbox-modal")
    modal_bg = page.evaluate('el => window.getComputedStyle(el).backgroundColor', modal)
    assert '255, 255, 255' in modal_bg

    assert len(console_errors) == 0, f"Errors in browser console: {console_errors}"
