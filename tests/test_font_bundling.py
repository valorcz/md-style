"""
tests/test_font_bundling.py
Unit tests for FontBundler inlining and base64 WOFF2 embedding.
"""

from pathlib import Path
from core.fonts import FontBundler

def test_font_bundler_local_embedding(tmp_path):
    font_file = tmp_path / "mock_font.woff2"
    font_file.write_bytes(b"\x00\x01\x02\x03\x04\x05")

    css = f'@font-face {{ font-family: "TestFont"; src: url("{font_file.name}") format("woff2"); }}'

    bundler = FontBundler(cache_dir=tmp_path / "cache")
    result = bundler.process_css(css, tmp_path)

    assert "data:font/woff2;base64," in result
    assert "AAECAwQF" in result
