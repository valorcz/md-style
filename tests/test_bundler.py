"""
tests/test_bundler.py
Unit tests for AssetBundler and self-contained HTML assembly.
"""

from pathlib import Path
from core.bundler import AssetBundler
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
