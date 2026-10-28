"""
tests/test_cleanup.py
Verifies that legacy Pandoc/Lua filters, templates, and flat root stylesheets are removed.
"""

from pathlib import Path
from core.config import PROJECT_DIR, STYLES_DIR

def test_legacy_folders_removed():
    assert not (PROJECT_DIR / "filters").exists(), "filters/ folder must not exist"
    assert not (PROJECT_DIR / "templates").exists(), "templates/ folder must not exist"
    assert not (PROJECT_DIR / "core" / "enrichers").exists(), "core/enrichers/ must not exist"
    assert not (PROJECT_DIR / "core" / "providers").exists(), "core/providers/ must not exist"
    assert not (PROJECT_DIR / "core" / "knowledge.py").exists(), "core/knowledge.py must not exist"
    assert not (PROJECT_DIR / "core" / "inspector.py").exists(), "core/inspector.py must not exist"
    assert not (PROJECT_DIR / "vendor" / "octicons.lua").exists(), "vendor/octicons.lua must not exist"

def test_styles_root_clean():
    # Only directories should be present in styles/ (base, forensic, general, i18n, svj)
    flat_css_files = list(STYLES_DIR.glob("*.css"))
    assert len(flat_css_files) == 0, f"Found unexpected flat CSS in styles/: {flat_css_files}"
    flat_lua_files = list(STYLES_DIR.glob("**/*.lua"))
    assert len(flat_lua_files) == 0, f"Found unexpected Lua in styles/: {flat_lua_files}"
