"""
tests/test_font_bundling.py
Unit tests for FontBundler inlining and base64 WOFF2 embedding.
"""

from pathlib import Path
from core.fonts import FontBundler, resolve_font_subsets


def test_font_bundler_local_embedding(tmp_path):
    font_file = tmp_path / "mock_font.woff2"
    font_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")

    css = f'@font-face {{ font-family: "TestFont"; src: url("{font_file.name}") format("woff2"); }}'

    bundler = FontBundler(cache_dir=tmp_path / "cache")
    result = bundler.process_css(css, tmp_path)

    assert "data:font/woff2;base64," in result
    assert "AAECAwQF" in result


def test_resolve_font_subsets():
    # Default Latin languages
    assert resolve_font_subsets("en") == {"latin", "latin-ext"}
    assert resolve_font_subsets("cs") == {"latin", "latin-ext"}
    assert resolve_font_subsets("de") == {"latin", "latin-ext"}

    # Cyrillic languages
    assert resolve_font_subsets("ru") == {"latin", "latin-ext", "cyrillic", "cyrillic-ext"}
    assert resolve_font_subsets("uk") == {"latin", "latin-ext", "cyrillic", "cyrillic-ext"}

    # Greek
    assert resolve_font_subsets("el") == {"latin", "latin-ext", "greek", "greek-ext"}

    # Vietnamese
    assert resolve_font_subsets("vi") == {"latin", "latin-ext", "vietnamese"}

    # All fonts / no prune
    assert resolve_font_subsets("en", all_fonts=True) is None
    assert resolve_font_subsets("cs", font_subsets_opt="all") is None
    assert resolve_font_subsets("cs", frontmatter_subsets="all") is None

    # Custom subsets
    assert resolve_font_subsets("en", font_subsets_opt="latin,cyrillic") == {"latin", "cyrillic"}
    assert resolve_font_subsets("cs", frontmatter_subsets=["latin", "greek"]) == {"latin", "greek"}


def test_font_bundler_subset_pruning(tmp_path):
    css = """
/* cyrillic */
@font-face {
  font-family: 'Inter';
  src: url('mock_cyrillic.woff2') format('woff2');
}
/* latin */
@font-face {
  font-family: 'Inter';
  src: url('mock_latin.woff2') format('woff2');
}
"""
    (tmp_path / "mock_cyrillic.woff2").write_bytes(b"CYRILLIC")
    (tmp_path / "mock_latin.woff2").write_bytes(b"LATIN")

    bundler = FontBundler(cache_dir=tmp_path / "cache", subsets={"latin"})
    processed = bundler.process_css(css, tmp_path)

    assert "mock_latin.woff2" not in processed
    assert "data:font/woff2;base64," in processed
    assert "Pruned font subset: cyrillic" in processed


def test_diagram_font_deduplication(tmp_path):
    from core.bundler import AssetBundler

    html_fragment = '''
<figure class="mermaid-diagram">
  <svg>
    <style>
      @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;700&display=swap');
      text { font-family: 'Inter', sans-serif; }
    </style>
    <text>Diagram Label</text>
  </svg>
</figure>
'''
    doc_path = tmp_path / "report.md"
    doc_path.write_text("# Test", encoding="utf-8")

    # 1. Default (dedup_diagram_fonts=True): @import is stripped/deduplicated
    bundler_dedup = AssetBundler(doc_path, allow_online=False, dedup_diagram_fonts=True)
    sanitized = bundler_dedup.sanitize_inline_styles(html_fragment)
    assert "Fonts inherited from document theme" in sanitized
    assert "fonts.googleapis.com" not in sanitized

    # 2. Disabled dedup (dedup_diagram_fonts=False): remote @import is retained for processing
    bundler_no_dedup = AssetBundler(doc_path, allow_online=False, dedup_diagram_fonts=False)
    sanitized_no_dedup = bundler_no_dedup.sanitize_inline_styles(html_fragment)
    assert "Fonts inherited from document theme" not in sanitized_no_dedup

