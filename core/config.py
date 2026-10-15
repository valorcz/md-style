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
PRINT_PDF_SCRIPT = VIEWER_DIR / "scripts" / "print-pdf.mjs"

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
CVE_DB_PATH = DATA_DIR / "cve.json"
CVE_CACHE_PATH = INTEL_CACHE_DIR / "cve.json"
CWE_DB_PATH = DATA_DIR / "cwe.json"
CWE_CACHE_PATH = INTEL_CACHE_DIR / "cwe.json"
GHSA_CACHE_PATH = INTEL_CACHE_DIR / "ghsa.json"
EVTX_CACHE_PATH = INTEL_CACHE_DIR / "evtx.json"
IP_CACHE_PATH = INTEL_CACHE_DIR / "ip.json"
HASH_CACHE_PATH = INTEL_CACHE_DIR / "hash.json"

DEFAULT_MITRE_CWE_URL = "https://cwe.mitre.org/data/xml/cwec_latest.xml.zip"

# Platform-Standard User Configuration Resolution (~/.config/md-style/)
def get_user_config_dir() -> Path:
    """Returns platform-standard user config directory for md-style."""
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or (Path.home() / "AppData" / "Roaming")
        return Path(base) / "md-style"
    else:
        xdg = os.environ.get("XDG_CONFIG_HOME")
        base = Path(xdg) if xdg else (Path.home() / ".config")
        return base / "md-style"

CONFIG_DIR = get_user_config_dir()


def load_user_config() -> dict:
    """
    Loads user configuration from ~/.config/md-style/
    Supports cascading lookup:
      1. config.yaml / config.yml
      2. config.toml
      3. config.json
    """
    candidates = [
        CONFIG_DIR / "config.yaml",
        CONFIG_DIR / "config.yml",
        CONFIG_DIR / "config.toml",
        CONFIG_DIR / "config.json"
    ]
    for p in candidates:
        if p.exists():
            try:
                if p.suffix in [".yaml", ".yml"]:
                    import yaml
                    return yaml.safe_load(p.read_text(encoding="utf-8")) or {}
                elif p.suffix == ".toml":
                    try:
                        import tomllib
                        return tomllib.loads(p.read_text(encoding="utf-8"))
                    except ImportError:
                        import tomli
                        return tomli.loads(p.read_text(encoding="utf-8"))
                elif p.suffix == ".json":
                    import json
                    return json.loads(p.read_text(encoding="utf-8"))
            except Exception:
                pass
    return {}


def get_threat_intel_api_key(service: str) -> str:
    """
    Retrieves API key for a threat intel service (e.g. 'shodan', 'virustotal', 'abuseipdb').
    Precedence:
      1. Environment variables (e.g. MD_STYLE_SHODAN_KEY, MD_STYLE_VT_KEY)
      2. ~/.config/md-style/config.[yaml|toml|json] under threat_intel.<service>.api_key or <service>.api_key
    """
    env_map = {
        "shodan": "MD_STYLE_SHODAN_KEY",
        "virustotal": "MD_STYLE_VT_KEY",
        "abuseipdb": "MD_STYLE_ABUSEIPDB_KEY",
        "greynoise": "MD_STYLE_GREYNOISE_KEY"
    }
    env_var = env_map.get(service.lower())
    if env_var and os.environ.get(env_var):
        return os.environ[env_var].strip()

    cfg = load_user_config()
    ti = cfg.get("threat_intel") or cfg
    svc_cfg = ti.get(service.lower()) or {}
    if isinstance(svc_cfg, dict):
        return svc_cfg.get("api_key", "").strip()
    elif isinstance(svc_cfg, str):
        return svc_cfg.strip()

    return ""


def ensure_directories():
    """Ensures static, user cache, and user config directories exist."""
    STATIC_DIR.mkdir(parents=True, exist_ok=True)
    ICONS_DIR.mkdir(parents=True, exist_ok=True)
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    FONTS_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    INTEL_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)

ensure_directories()
