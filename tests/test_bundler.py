"""
tests/test_bundler.py
Unit tests for AssetBundler and self-contained HTML assembly.
"""

from pathlib import Path
from core.bundler import (
    AssetBundler,
    compute_bundle_size_breakdown,
    format_bundle_size_breakdown,
)
from core.themes import ThemeResolver
from core.kb.models import KnowledgePack, Entity

def test_asset_bundler_self_contained(tmp_path):
    doc_path = tmp_path / "report.md"
    doc_path.write_text("# Test\n", encoding="utf-8")

    resolver = ThemeResolver()
    theme = resolver.resolve("forensic/cyber")

    pack = KnowledgePack()
    pack.entities["CVE-1"] = Entity(id="CVE-1", domain="cyber", type="cve", label="CVE-1", title="Test CVE")

    bundler = AssetBundler(doc_path)
    html = bundler.assemble(
        html_fragment="<p>Test</p>",
        theme=theme,
        knowledge_pack=pack,
        title="Test Document"
    )

    assert "<!DOCTYPE html>" in html
    assert "/* Theme Variables */" in html
    assert "id=\"md-style-viewer-root\"" in html
    assert "id=\"md-style-kb-data\"" in html
    assert "<link rel=\"stylesheet\"" not in html
    assert "<script src=\"http" not in html

    breakdown = compute_bundle_size_breakdown(html)
    assert breakdown["total"] == len(html.encode("utf-8"))
    assert breakdown["fonts"] > 0
    assert breakdown["viewer_js"] > 0
    assert breakdown["css"] > 0
    assert breakdown["metadata"] > 0
    assert breakdown["content"] > 0

    formatted = format_bundle_size_breakdown(breakdown)
    assert "Fonts:" in formatted
    assert "Viewer JS:" in formatted
    assert "CSS:" in formatted
    assert "Data:" in formatted
    assert "Content:" in formatted


def test_bundle_size_breakdown_empty_and_nonexistent(tmp_path):
    assert compute_bundle_size_breakdown("") == {
        "total": 0, "fonts": 0, "viewer_js": 0, "css": 0, "metadata": 0, "diagrams": 0, "images": 0, "content": 0
    }
    assert compute_bundle_size_breakdown(tmp_path / "nonexistent.html") == {
        "total": 0, "fonts": 0, "viewer_js": 0, "css": 0, "metadata": 0, "diagrams": 0, "images": 0, "content": 0
    }
    assert format_bundle_size_breakdown({}) == ""

