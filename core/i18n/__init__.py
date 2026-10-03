"""
core/i18n/__init__.py
Layered Cascading Localization Engine for md-style.
Integrates Babel (Unicode CLDR) and cascading JSON locale catalogs:
  Frontmatter Overrides -> Style-specific Locale -> Core Locale -> English Fallback
"""

import json
import re
from pathlib import Path
from typing import Dict, Any, Optional, List

try:
    from babel import Locale
    from babel.dates import format_datetime, format_date
    HAS_BABEL = True
except ImportError:
    HAS_BABEL = False

from core.config import PROJECT_DIR

I18N_CORE_DIR = Path(__file__).parent
STYLES_I18N_DIR = PROJECT_DIR / "styles" / "i18n"

def normalize_locale(lang: Optional[str]) -> str:
    """Normalizes language code into standard 2-letter ISO 639-1 code."""
    if not lang:
        return "en"
    clean = lang.strip().replace("_", "-")
    if clean.lower() in ("cz", "czech"):
        return "cs"
    if HAS_BABEL:
        try:
            loc = Locale.parse(clean, sep="-")
            return loc.language
        except Exception:
            pass
    # Regex fallback
    m = re.match(r"^([a-zA-Z]{2})", clean)
    return m.group(1).lower() if m else "en"

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merges override dictionary into a copy of base dictionary."""
    result = dict(base)
    for k, v in override.items():
        if k in result and isinstance(result[k], dict) and isinstance(v, dict):
            result[k] = deep_merge(result[k], v)
        else:
            result[k] = v
    return result

def _load_json_file(path: Path) -> Dict[str, Any]:
    if path.is_file():
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except Exception:
            return {}
    return {}

def resolve_style_family(style_name: Optional[str]) -> Optional[str]:
    """Maps specific style variant names to their i18n family folder."""
    if not style_name:
        return None
    s = style_name.lower()
    if s.startswith("svj"):
        return "svj"
    if s == "forensic-cyber":
        return "forensic-cyber"
    if s == "forensic":
        return "forensic"
    if s == "school":
        return "school"
    if s == "announcement":
        return "announcement"
    return s

def resolve_locale(
    lang: Optional[str] = "en",
    style_name: Optional[str] = None,
    frontmatter: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Resolves the cascading locale catalog for the specified language and style.
    Hierarchy:
      1. Core en.json (universal fallback)
      2. Core {lang}.json
      3. Style {family}/en.json (style fallback)
      4. Style {family}/{lang}.json (style specific)
      5. Frontmatter overrides (document specific)
    """
    code = normalize_locale(lang)

    # 1. Base core fallback
    catalog = _load_json_file(I18N_CORE_DIR / "en.json")

    # 2. Base core requested lang
    if code != "en":
        core_lang = _load_json_file(I18N_CORE_DIR / f"{code}.json")
        catalog = deep_merge(catalog, core_lang)

    # Style resolution with family cascading
    family = resolve_style_family(style_name)
    if family:
        # Check if sub-style extends a major family (e.g. forensic-cyber extends forensic)
        base_family = None
        if family == "forensic-cyber" or (style_name and style_name.startswith("forensic/")):
            base_family = "forensic"

        # 3. Base family catalog if applicable
        if base_family and base_family != family:
            base_dir = STYLES_I18N_DIR / base_family
            base_en = _load_json_file(base_dir / "en.json")
            catalog = deep_merge(catalog, base_en)
            if code != "en":
                base_lang = _load_json_file(base_dir / f"{code}.json")
                catalog = deep_merge(catalog, base_lang)

        # 4. Specific style catalog
        style_dir = STYLES_I18N_DIR / family
        style_en = _load_json_file(style_dir / "en.json")
        catalog = deep_merge(catalog, style_en)
        if code != "en":
            style_lang = _load_json_file(style_dir / f"{code}.json")
            catalog = deep_merge(catalog, style_lang)

    # 5. Frontmatter explicit overrides
    if frontmatter:
        meta_overrides = {}
        # Classification
        clf = frontmatter.get("classification") or frontmatter.get("confidentiality-label")
        if clf:
            meta_overrides["confidential_label"] = str(clf)
        # Report type
        rtype = frontmatter.get("report-type") or frontmatter.get("report-badge")
        if rtype:
            meta_overrides["report_type"] = str(rtype)
        # Examiner / Author
        author = frontmatter.get("examiner-label") or frontmatter.get("author-label")
        if author:
            meta_overrides["examiner_label"] = str(author)
        # Date
        dt_label = frontmatter.get("date-label")
        if dt_label:
            meta_overrides["date_label"] = str(dt_label)
        # TOC & Abstract
        if "toc-title" in frontmatter:
            meta_overrides["toc_title"] = str(frontmatter["toc-title"])
        if "abstract-title" in frontmatter:
            meta_overrides["abstract_title"] = str(frontmatter["abstract-title"])

        if meta_overrides:
            catalog["meta"] = deep_merge(catalog.get("meta", {}), meta_overrides)

    catalog["code"] = code
    return catalog

def generate_pandoc_metadata_args(catalog: Dict[str, Any]) -> List[str]:
    """Generates CLI --metadata arguments for Pandoc AST localization."""
    args = []
    meta = catalog.get("meta", {})
    code = catalog.get("code", "en")
    
    args.append(f"--metadata=lang:{code}")
    if "toc_title" in meta:
        args.append(f"--metadata=toc-title:{meta['toc_title']}")
    if "abstract_title" in meta:
        args.append(f"--metadata=abstract-title:{meta['abstract_title']}")
    if "figure_label" in meta:
        args.append(f"--metadata=figure-title:{meta['figure_label']}")
    if "table_label" in meta:
        args.append(f"--metadata=table-title:{meta['table_label']}")

    return args

def generate_css_custom_properties(catalog: Dict[str, Any]) -> str:
    """Generates CSS custom properties matching or overriding legacy :root:lang(...) stylesheet rules."""
    meta = catalog.get("meta", {})
    code = catalog.get("code", "en")
    lines = [
        f":root, :root:lang({code}), html[lang^='{code}'] {{"
    ]

    STANDARD_ALIAS_MAP = {
        "confidential_label": "--i18n-confidential",
        "report_type": "--i18n-report-title",
        "examiner_label": "--i18n-examiner",
        "date_label": "--i18n-date",
        "author_label": "--i18n-author",
        "figure_label": "--i18n-figure",
        "table_label": "--i18n-table",
        "page_prefix": "--i18n-page-prefix",
        "page_of": "--i18n-page-of",
        "section_tag": "--i18n-section-tag",
        "hex_dump": "--i18n-hex-dump",
        "sys_log": "--i18n-sys-log",
    }

    emitted_vars = set()
    for k, v in meta.items():
        if k in STANDARD_ALIAS_MAP:
            var_name = STANDARD_ALIAS_MAP[k]
        elif k.startswith("--"):
            var_name = k
        else:
            var_name = f"--{k.replace('_', '-')}"

        if var_name not in emitted_vars:
            lines.append(f'  {var_name}: "{v}";')
            emitted_vars.add(var_name)

    lines.append("}")
    return "\n".join(lines)

def list_supported_languages() -> List[str]:
    """Lists languages available in core catalogs."""
    langs = []
    for f in I18N_CORE_DIR.glob("*.json"):
        langs.append(f.stem)
    return sorted(langs)
