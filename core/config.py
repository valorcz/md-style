"""
core/config.py
Configuration constants and path resolution for the pure-Python report pipeline.
Adheres to standard OS cache directories (XDG on Linux) and static asset directories.
"""

import os
import sys
from pathlib import Path

# Base Directories
CORE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = CORE_DIR.parent
STATIC_DIR = PROJECT_DIR / "static"
ICONS_DIR = STATIC_DIR / "icons"
STYLES_DIR = PROJECT_DIR / "styles"
VIEWER_DIR = PROJECT_DIR / "viewer"
MERMAID_SCRIPT = VIEWER_DIR / "scripts" / "render-diagram.mjs"

# Platform-Standard User Cache Resolution
def get_user_cache_dir() -> Path:
    """Returns platform-standard user cache directory for md-style."""
    if sys.platform == "win32":
        base = os.environ.get("LOCALAPPDATA") or (Path.home() / "AppData" / "Local")
        return Path(base) / "md-style" / "Cache"
    elif sys.platform == "darwin":
        return Path.home() / "Library" / "Caches" / "md-style"
    else:
        xdg = os.environ.get("XDG_CACHE_HOME")
        base = Path(xdg) if xdg else (Path.home() / ".cache")
        return base / "md-style"

CACHE_DIR = get_user_cache_dir()
FONTS_CACHE_DIR = CACHE_DIR / "fonts"
INTEL_CACHE_DIR = CACHE_DIR / "intel"

# Pre-compiled Knowledge Datasets
DATA_DIR = PROJECT_DIR / "data"
MITRE_DB_PATH = DATA_DIR / "mitre-attack.json"
WIN_EVENTS_DB_PATH = DATA_DIR / "windows-events.json"
WIN_EVENTS_CACHE_PATH = INTEL_CACHE_DIR / "windows-events.json"
CVE_CACHE_PATH = INTEL_CACHE_DIR / "cve.json"
GHSA_CACHE_PATH = INTEL_CACHE_DIR / "ghsa.json"

def ensure_directories():
    """Ensures static and user cache directories exist."""
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    FONTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    INTEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)

ensure_directories()
