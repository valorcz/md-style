"""
core/config.py
Configuration constants and path resolution for the modular report pipeline.
"""

import os
from pathlib import Path

# Base Directories
CORE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = CORE_DIR.parent
DATA_DIR = PROJECT_DIR / "data"
CACHE_DIR = DATA_DIR / "cache"
STYLES_DIR = PROJECT_DIR / "styles"
TEMPLATES_DIR = PROJECT_DIR / "templates"
FILTERS_DIR = PROJECT_DIR / "filters"
VENDOR_DIR = PROJECT_DIR / "vendor"

# Pre-compiled Knowledge Datasets
MITRE_DB_PATH = DATA_DIR / "mitre-attack.json"
WIN_EVENTS_DB_PATH = DATA_DIR / "windows-events.json"
WIN_EVENTS_CACHE_PATH = CACHE_DIR / "windows-events.json"
CVE_CACHE_PATH = CACHE_DIR / "cve.json"
GHSA_CACHE_PATH = CACHE_DIR / "ghsa.json"

# Diagram Renderers
MERMAID_BUNDLE = VENDOR_DIR / "beautiful-mermaid.bundle.mjs"

# Interactive Templates
TEMPLATES = {
    "forensic": TEMPLATES_DIR / "forensic-interactive.html",
    "forensic-cyber": TEMPLATES_DIR / "forensic-cyber-interactive.html",
    "print-action": TEMPLATES_DIR / "print-action.html",
    "paged-header": TEMPLATES_DIR / "paged-header.html"
}

# Style Metadata & Hierarchical Families
STYLE_CATEGORIES = {
    "forensic": [
        "forensic/cyber (alias: forensic-cyber)",
        "forensic/dossier (alias: forensic)"
    ],
    "svj": [
        "svj/modern (alias: svj-modern)",
        "svj/ballot (alias: svj-ballot)",
        "svj/invitation (alias: svj-invitation)",
        "svj/community (alias: svj-community)",
        "svj/typewriter (alias: svj-typewriter)"
    ],
    "general": [
        "school",
        "announcement"
    ]
}

def ensure_directories():
    """Ensures data and cache directories exist."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)

ensure_directories()
