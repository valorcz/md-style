"""
core/frontmatter.py
Frontmatter normalization and namespaced option retrieval.
Supports grouping md-style specific configuration under `md-style:` or `md_style:`
to avoid collisions with Obsidian, Pandoc, Zettlr, Jekyll, or other markdown frontmatter parsers,
while preserving full backward compatibility with top-level keys.
"""

from typing import Dict, Any, Optional

MD_STYLE_NAMESPACES = ("md-style", "md_style", "mdstyle")


def normalize_frontmatter(raw_fm: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Normalizes frontmatter dictionary.
    If 'md-style' (or 'md_style') namespace is present, merges its keys into
    the top-level dictionary (with namespace taking precedence over root keys)
    while keeping the original namespace block intact.

    Also normalizes common boolean and alias variations:
      - viewer <-> interactive_viewer <-> interactive
      - theme <-> style
      - language <-> lang
    """
    if not raw_fm or not isinstance(raw_fm, dict):
        return {}

    result = dict(raw_fm)

    # 1. Merge namespaced configuration blocks (with precedence)
    for ns in MD_STYLE_NAMESPACES:
        sub = raw_fm.get(ns)
        if isinstance(sub, dict):
            for k, v in sub.items():
                result[k] = v

    # 2. Alias normalization: viewer / interactive_viewer / interactive
    viewer_val = None
    if "interactive_viewer" in result:
        viewer_val = result["interactive_viewer"]
    elif "viewer" in result:
        viewer_val = result["viewer"]
    elif "interactive" in result:
        viewer_val = result["interactive"]

    if viewer_val is not None:
        if isinstance(viewer_val, str):
            b_val = viewer_val.strip().lower() not in ("false", "no", "off", "0", "disable", "disabled")
        else:
            b_val = bool(viewer_val)
        result["interactive_viewer"] = b_val
        result["viewer"] = b_val

    # 3. Alias normalization: theme <-> style
    if "style" in result and "theme" not in result:
        result["theme"] = result["style"]
    elif "theme" in result and "style" not in result:
        result["style"] = result["theme"]

    # 4. Alias normalization: language <-> lang
    if "lang" in result and "language" not in result:
        result["language"] = result["lang"]
    elif "language" in result and "lang" not in result:
        result["lang"] = result["language"]

    return result


def get_frontmatter_option(fm: Optional[Dict[str, Any]], key: str, default: Any = None) -> Any:
    """
    Safely retrieves a configuration key from frontmatter, checking
    namespaced blocks first ('md-style', 'md_style', 'mdstyle'), then top-level.
    """
    if not fm or not isinstance(fm, dict):
        return default

    for ns in MD_STYLE_NAMESPACES:
        sub = fm.get(ns)
        if isinstance(sub, dict) and key in sub:
            return sub[key]

    return fm.get(key, default)
