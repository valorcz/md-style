"""
core/bundler/paged_resolver.py
Resolves declarative Paged.js page geometry, margins, running headers, and footers into CSS variables.
"""

import re
import datetime
from typing import Dict, Any, Optional

from core.themes import ResolvedTheme
from core.i18n import I18nCatalog


class PagedVariableResolver:
    """Computes CSS custom properties for Paged.js page geometry and token interpolation."""

    @staticmethod
    def resolve_paged_variables(
        theme: ResolvedTheme,
        catalog: I18nCatalog,
        title: str,
        frontmatter: Optional[Dict[str, Any]] = None,
        fingerprint: str = ""
    ) -> Dict[str, str]:
        paged_cfg = getattr(theme, "paged", {}) or {}
        if not paged_cfg:
            return {}

        headers = paged_cfg.get("headers", {})
        footers = paged_cfg.get("footers", {})
        first_page = paged_cfg.get("first_page", {})
        margins = paged_cfg.get("margins", {})
        fm = frontmatter or {}

        doc_date = str(fm.get("date") or datetime.date.today().strftime("%Y-%m-%d"))
        classification = str(
            fm.get("classification")
            or catalog.get("forensics.classification")
            or catalog.get("meta.confidential_label")
            or "CONFIDENTIAL"
        )
        page_of = catalog.get("meta.page_of", " of ")
        page_counter_str = f'counter(page) {page_of} counter(pages)'

        context: Dict[str, Any] = {
            "doc_title": title,
            "title": title,
            "date": doc_date,
            "classification": classification,
            "page_counter": page_counter_str,
            "fingerprint": fingerprint[:16] if fingerprint else "",
            "fingerprint_short": fingerprint[:8] if fingerprint else "",
        }

        for k, v in fm.items():
            if isinstance(v, (str, int, float)):
                context[f"meta.{k}"] = str(v)
                context[k] = str(v)

        def interpolate(template: str) -> str:
            if not template:
                return ""

            def _repl(m: re.Match) -> str:
                raw_expr = m.group(1).strip()
                expr = raw_expr
                default_val = ""
                if "|" in raw_expr:
                    expr, default_val = raw_expr.split("|", 1)
                    expr = expr.strip()
                    default_val = default_val.strip()

                if expr in context and context[expr]:
                    return str(context[expr])
                if expr.startswith("i18n."):
                    i18n_key = expr[5:]
                    val = catalog.get(i18n_key)
                    if val:
                        return str(val)
                if default_val:
                    if default_val in context and context[default_val]:
                        return str(context[default_val])
                    return default_val
                return ""

            return re.sub(r"\{([^}]+)\}", _repl, template).strip()

        def format_css_val(val: str) -> str:
            if not val or val == "none":
                return "none"
            if val in {"string(heading)", "string(section-title)"}:
                return val
            parts = re.split(r"(counter\([^)]+\)|string\([^)]+\))", val)
            if len(parts) == 1:
                escaped = val.replace('"', '\\"')
                return f'"{escaped}"'
            css_parts = []
            for p in parts:
                if not p:
                    continue
                if re.match(r"^(counter|string)\([^)]+\)$", p):
                    css_parts.append(p)
                else:
                    clean_p = p.strip()
                    if clean_p:
                        escaped = clean_p.replace('"', '\\"')
                        css_parts.append(f'" {escaped} "')
            return " ".join(css_parts)

        vars_dict: Dict[str, str] = {}
        if "size" in paged_cfg:
            vars_dict["--page-size"] = paged_cfg["size"]
        if margins:
            top = margins.get("top", "22mm")
            right = margins.get("right", "18mm")
            bottom = margins.get("bottom", "22mm")
            left = margins.get("left", "18mm")
            vars_dict["--page-margin"] = f"{top} {right} {bottom} {left}"

        h_left = interpolate(headers.get("left", ""))
        h_center = interpolate(headers.get("center", ""))
        h_right = interpolate(headers.get("right", ""))

        if h_left:
            vars_dict["--page-header-left"] = format_css_val(h_left)
        if h_center:
            vars_dict["--page-header-center"] = format_css_val(h_center)
        if h_right:
            vars_dict["--page-header-right"] = format_css_val(h_right)

        f_left = interpolate(footers.get("left", ""))
        f_center = interpolate(footers.get("center", ""))
        f_right = interpolate(footers.get("right", ""))

        if f_left:
            vars_dict["--page-footer-left"] = format_css_val(f_left)
        if f_center:
            vars_dict["--page-footer-center"] = format_css_val(f_center)
        if f_right:
            vars_dict["--page-footer-right"] = format_css_val(f_right)

        if not first_page.get("show_header", True):
            vars_dict["--page-first-header-left"] = "none"
            vars_dict["--page-first-header-center"] = "none"
            vars_dict["--page-first-header-right"] = "none"
        if not first_page.get("show_footer", True):
            vars_dict["--page-first-footer-left"] = "none"
            vars_dict["--page-first-footer-center"] = "none"
            vars_dict["--page-first-footer-right"] = "none"

        return vars_dict
