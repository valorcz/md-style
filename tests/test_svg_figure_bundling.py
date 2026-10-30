"""
tests/test_svg_figure_bundling.py
End-to-end and integration tests verifying SVG figure generation, sequential numbering,
multi-root asset resolution, build-time diagnostics, and font embedding.
"""

import tempfile
from pathlib import Path
from core.parser.engine import MarkdownParser
from core.bundler import AssetBundler
from core.themes import ThemeResolver
from core.diagnostics import Diagnostics


def test_markdown_parser_standalone_image_becomes_figure():
    """Verifies standalone block image becomes semantic <figure> with localized caption."""
    parser = MarkdownParser(lang="cs")
    md_content = """
# Test Document

![Architektura sítě](assets/network.svg "Schéma infrastruktury")

Odhadovaný text.
"""
    html_out, toc, meta = parser.render(md_content)
    assert 'class="doc-figure figure-container svg-figure"' in html_out
    assert 'class="svg-container"' in html_out
    assert '<figcaption class="svg-caption">' in html_out
    assert '<span class="figure-label">Obrázek 1:</span>' in html_out
    assert 'Schéma infrastruktury' in html_out


def test_figure_sequential_numbering_shared_with_mermaid():
    """Verifies Mermaid diagrams and SVG figures share a unified sequential numbering sequence."""
    parser = MarkdownParser(lang="en", enable_mermaid=True)
    md_content = """
```mermaid caption="Data Flow Diagram"
flowchart TD
  A --> B
```

![Network Map](assets/network.svg "Network Map Title")

```mermaid caption="State Transition"
stateDiagram-v2
  [*] --> Active
```
"""
    html_out, _, _ = parser.render(md_content)
    # Figure 1: Data Flow Diagram
    assert "Figure 1:" in html_out
    assert "Data Flow Diagram" in html_out
    # Figure 2: Network Map Title
    assert "Figure 2:" in html_out
    assert "Network Map Title" in html_out
    # Figure 3: State Transition
    assert "Figure 3:" in html_out
    assert "State Transition" in html_out


def test_asset_bundler_multi_root_resolution_and_svg_inlining(tmp_path):
    """
    Verifies AssetBundler resolves assets across parent directory and inlines SVG directly into the DOM.
    """
    # Create project layout:
    # root/
    #   assets/
    #     diagram.svg
    #   dist/
    #     report.md
    root_dir = tmp_path / "project"
    assets_dir = root_dir / "assets"
    dist_dir = root_dir / "dist"
    assets_dir.mkdir(parents=True)
    dist_dir.mkdir(parents=True)

    svg_file = assets_dir / "diagram.svg"
    svg_file.write_text(
        '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 200 100">'
        '<defs><style>text { fill: blue; }</style></defs>'
        '<text x="10" y="20">Hello World</text>'
        '</svg>',
        encoding="utf-8"
    )

    doc_file = dist_dir / "report.md"
    doc_file.write_text(
        "![Sample Diagram](assets/diagram.svg)",
        encoding="utf-8"
    )

    # 1. Parse markdown
    parser = MarkdownParser(lang="en")
    html_frag, _, _ = parser.render(doc_file.read_text(encoding="utf-8"))

    # 2. Bundle with AssetBundler whose doc_path is inside dist/
    bundler = AssetBundler(doc_file, allow_online=True)
    theme_resolver = ThemeResolver()
    theme = theme_resolver.resolve("base")

    bundled_html = bundler.assemble(
        html_fragment=html_frag,
        theme=theme,
        title="Test Report",
        lang="en"
    )

    # Asset in ../assets/diagram.svg was successfully resolved!
    assert 'class="svg-inlined-wrapper"' in bundled_html
    # Inlined as native <svg>, NOT left as unbundled <img src="assets/diagram.svg">
    assert 'src="assets/diagram.svg"' not in bundled_html
    assert '<svg xmlns="http://www.w3.org/2000/svg"' in bundled_html
    assert 'Hello World' in bundled_html
    # Scoped style
    assert "text { fill: blue; }" in bundled_html or "text { fill: blue;}" in bundled_html


def test_asset_bundler_missing_asset_warning(capsys, tmp_path):
    """Verifies AssetBundler emits an explicit build-time diagnostic warning on missing images."""
    doc_file = tmp_path / "doc.md"
    doc_file.write_text("![Missing Image](assets/non_existent.svg)", encoding="utf-8")

    parser = MarkdownParser(lang="en")
    html_frag, _, _ = parser.render(doc_file.read_text(encoding="utf-8"))

    bundler = AssetBundler(doc_file, allow_online=False)
    theme_resolver = ThemeResolver()
    theme = theme_resolver.resolve("base")

    bundler.assemble(
        html_fragment=html_frag,
        theme=theme,
        title="Missing Asset Test",
        lang="en"
    )

    captured = capsys.readouterr()
    assert "non_existent.svg" in captured.err
    assert "could not be resolved on disk" in captured.err or "Checked" in captured.err


def test_svg_figure_sizing_attributes_and_classes(tmp_path):
    """Verifies image width/style attributes and sizing classes ({.wide}, {width=500px}) are applied."""
    svg_file = tmp_path / "diagram.svg"
    svg_file.write_text('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 100 100"><circle r="50"/></svg>', encoding="utf-8")

    doc_file = tmp_path / "doc.md"
    doc_file.write_text(
        "![Explicit Width](diagram.svg){width=500px}\n\n"
        "![Wide Breakout](diagram.svg){.wide}\n",
        encoding="utf-8"
    )

    parser = MarkdownParser(lang="en")
    html_frag, _, _ = parser.render(doc_file.read_text(encoding="utf-8"))

    # Check Markdown figure transformation
    assert 'style="max-width: 500px;"' in html_frag
    assert 'class="doc-figure figure-container svg-figure wide"' in html_frag

    bundler = AssetBundler(doc_file, allow_online=False)
    theme = ThemeResolver().resolve("base")
    bundled_html = bundler.assemble(html_frag, theme=theme)

    # Check that width style transferred to inlined wrapper
    assert 'max-width: 500px;' in bundled_html
    assert 'class="doc-figure figure-container svg-figure wide"' in bundled_html


def test_figure_css_scoping_protects_toolbar_icons():
    """Verifies that figure CSS selectors in figures.css target inner containers, protecting toolbar SVGs."""
    figures_css_path = Path(__file__).resolve().parent.parent / "styles" / "base" / "figures.css"
    css_content = figures_css_path.read_text(encoding="utf-8")

    # Invariant: naked 'figure.figure-container svg' or 'figure.figure-container.small svg'
    # would blow up toolbar icons in Svelte viewer
    assert "figure.figure-container svg {" not in css_content
    assert "figure.figure-container.small svg {" not in css_content
    assert "figure.figure-container .svg-container svg" in css_content
    assert "figure.figure-container .svg-inlined-wrapper svg" in css_content


