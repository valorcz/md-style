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
    from babel.dates import format_datetime as babel_format_datetime, format_date as babel_format_date
    from babel.numbers import format_decimal as babel_format_decimal
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
    if clean.lower() in ("sk", "slovak"):
        return "sk"
    if clean.lower() in ("de", "german"):
        return "de"
    if HAS_BABEL:
        try:
            loc = Locale.parse(clean, sep="-")
            return loc.language
        except Exception:
            pass
    m = re.match(r"^([a-zA-Z]{2})", clean)
    return m.group(1).lower() if m else "en"

def deep_merge(base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
    """Recursively merges override dictionary into base dictionary."""
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

class I18nCatalog:
    """Provides translated strings with cascading fallbacks and Babel CLDR formatting."""

    def __init__(
        self,
        lang: str = "en",
        style_family: Optional[str] = None,
        frontmatter: Optional[Dict[str, Any]] = None,
        custom_file: Optional[Path] = None
    ):
        self.code = normalize_locale(lang)
        self.catalog = self._resolve_catalog(self.code, style_family, frontmatter, custom_file)

    def _resolve_catalog(
        self,
        lang: str,
        style_family: Optional[str],
        frontmatter: Optional[Dict[str, Any]],
        custom_file: Optional[Path] = None
    ) -> Dict[str, Any]:
        # 1. Base English fallback
        en_catalog = _load_json_file(I18N_CORE_DIR / "en.json")

        # 2. Target language catalog
        target_catalog = en_catalog
        if lang != "en":
            lang_file = I18N_CORE_DIR / f"{lang}.json"
            if lang_file.is_file():
                target_catalog = deep_merge(en_catalog, _load_json_file(lang_file))

        # 3. Style-specific overrides
        if style_family:
            clean_family = style_family.split("/")[0].lower()
            style_en = STYLES_I18N_DIR / clean_family / "en.json"
            if style_en.is_file():
                target_catalog = deep_merge(target_catalog, _load_json_file(style_en))
            if lang != "en":
                style_lang = STYLES_I18N_DIR / clean_family / f"{lang}.json"
                if style_lang.is_file():
                    target_catalog = deep_merge(target_catalog, _load_json_file(style_lang))

        # 4. Custom external i18n file overlay (CLI --i18n)
        if custom_file and Path(custom_file).is_file():
            target_catalog = deep_merge(target_catalog, _load_json_file(Path(custom_file)))

        # 5. Frontmatter document-level overrides
        if frontmatter and "i18n" in frontmatter and isinstance(frontmatter["i18n"], dict):
            target_catalog = deep_merge(target_catalog, frontmatter["i18n"])

        return target_catalog

    def t(self, key_path: str, default: Optional[str] = None, **kwargs) -> str:
        """
        Retrieves a translated string using dot-notation (e.g. 'callouts.note', 'ui.copy').
        Interpolates kwargs if provided.
        """
        parts = key_path.strip().split(".")
        curr: Any = self.catalog
        for part in parts:
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            else:
                curr = None
                break

        if curr is None or not isinstance(curr, str):
            val = default if default is not None else parts[-1].upper()
        else:
            val = curr

        if kwargs:
            try:
                return val.format(**kwargs)
            except Exception:
                return val
        return val

    def get(self, key_path: str, default: Optional[str] = None) -> Optional[str]:
        """Safely retrieves a translated string or returns default if not found."""
        parts = key_path.strip().split(".")
        curr: Any = self.catalog
        for part in parts:
            if isinstance(curr, dict) and part in curr:
                curr = curr[part]
            else:
                return default
        return curr if isinstance(curr, str) else default

    def export_ui_dict(self) -> Dict[str, Any]:
        """Returns the UI dictionary for frontend injection."""
        return self.export_full_dict()

    def export_full_dict(self) -> Dict[str, Any]:
        """Returns full catalog plus flattened dot-path keys and top-level ui keys for direct access in Svelte."""
        res: Dict[str, Any] = dict(self.catalog)

        # Include direct ui shortcuts (e.g. res["copy"] = res["ui"]["copy"])
        ui_dict = self.catalog.get("ui", {})
        if isinstance(ui_dict, dict):
            for k, v in ui_dict.items():
                if isinstance(v, str):
                    res[k] = v

        def _flatten(d: dict, prefix: str = ""):
            for k, v in d.items():
                p = f"{prefix}.{k}" if prefix else k
                if isinstance(v, dict):
                    _flatten(v, p)
                elif isinstance(v, str):
                    res[p] = v

        _flatten(self.catalog)
        return res

    def export_css_variables(self) -> Dict[str, str]:
        """Exports CSS custom properties for pseudo-elements and headers (e.g. --i18n-examiner)."""
        vars_map: Dict[str, str] = {}

        # Special top-level convenience mappings with fallbacks
        convenience = [
            (["forensics.examiner", "meta.examiner_label", "meta.author_label"], "--i18n-examiner"),
            (["forensics.date", "meta.date_label"], "--i18n-date"),
            (["forensics.report_title", "meta.report_type"], "--i18n-report-title"),
            (["forensics.classification", "meta.confidential_label"], "--i18n-classification"),
            (["meta.section_tag"], "--i18n-section-tag"),
            (["meta.abstract_title"], "--i18n-abstract-title"),
            (["meta.toc_title", "toc.title"], "--i18n-toc-title"),
            (["meta.figure_prefix", "meta.figure_label"], "--i18n-figure-prefix"),
            (["meta.page_prefix", "meta.page_label"], "--i18n-page-prefix"),
            (["meta.page_of"], "--i18n-page-of"),
        ]
        for keys, css_var in convenience:
            for k in keys:
                val = self.get(k)
                if val:
                    vars_map[css_var] = f'"{val}"'
                    break

        def _walk(d: dict, prefix: str = ""):
            for k, v in d.items():
                full_k = f"{prefix}-{k}".lower() if prefix else k.lower()
                clean_k = full_k.replace("_", "-")
                if isinstance(v, dict):
                    _walk(v, clean_k)
                elif isinstance(v, str):
                    css_name = f"--i18n-{clean_k}"
                    if css_name not in vars_map:
                        vars_map[css_name] = f'"{v}"'

        _walk(self.catalog)
        return vars_map

    def format_date(self, dt, format: str = "medium") -> str:
        if HAS_BABEL:
            try:
                return babel_format_date(dt, format=format, locale=self.code)
            except Exception:
                pass
        return str(dt)

    def format_datetime(self, dt, format: str = "medium") -> str:
        if HAS_BABEL:
            try:
                return babel_format_datetime(dt, format=format, locale=self.code)
            except Exception:
                pass
        return str(dt)

def resolve_locale(
    lang: Optional[str] = "en",
    style_name: Optional[str] = None,
    frontmatter: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Compatibility function returning raw dictionary."""
    catalog = I18nCatalog(lang=lang or "en", style_family=style_name, frontmatter=frontmatter)
    return catalog.catalog
