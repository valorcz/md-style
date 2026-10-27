"""
core/bundler/cdp_template.py
Chromium CDP Print Header and Footer Template Builder.
"""

import re
import html
import datetime
from typing import Dict, Any, Optional

from core.i18n import I18nCatalog


class CdpTemplateBuilder:
    """Constructs native Chromium CDP header and footer HTML/CSS strings and page options."""

    @staticmethod
    def build(
        theme: Any,
        catalog: I18nCatalog,
        title: str,
        frontmatter: Optional[Dict[str, Any]] = None,
        fingerprint: str = ""
    ) -> Dict[str, Any]:
        paged_cfg = getattr(theme, "paged", {}) or {}
        headers = paged_cfg.get("headers", {})
        footers = paged_cfg.get("footers", {})
        margins = paged_cfg.get("margins", {})
        fm = frontmatter or {}

        doc_date = str(fm.get("date") or datetime.date.today().strftime("%Y-%m-%d"))
        classification = str(
            fm.get("classification")
            or catalog.get("forensics.classification")
            or catalog.get("meta.confidential_label")
            or "CONFIDENTIAL"
        )

        context: Dict[str, Any] = {
            "doc_title": title,
            "title": title,
            "date": doc_date,
            "classification": classification,
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

        h_left = interpolate(headers.get("left", ""))
        h_center = interpolate(headers.get("center", ""))
        h_right = interpolate(headers.get("right", ""))
        if h_right in {"string(heading)", "string(section-title)"}:
            h_right = ""

        f_left = interpolate(footers.get("left", ""))
        f_center = interpolate(footers.get("center", ""))
        f_right = interpolate(footers.get("right", ""))

        page_str = catalog.get("meta.page_label", "Page").strip()
        page_of = catalog.get("meta.page_of", "of").strip()
        page_widget = f'{page_str} <span class="pageNumber"></span> {page_of} <span class="totalPages"></span>'

        if not f_right or "page" in f_right.lower() or "counter" in f_right.lower():
            f_right = page_widget

        def parse_dim_inches(val: Any, default_in: float) -> float:
            if not val:
                return default_in
            s = str(val).strip().lower()
            m = re.match(r"^([\d\.]+)\s*(mm|cm|in|pt|px)?$", s)
            if not m:
                return default_in
            num = float(m.group(1))
            unit = m.group(2) or "mm"
            if unit == "mm":
                return round(num / 25.4, 3)
            elif unit == "cm":
                return round((num * 10) / 25.4, 3)
            elif unit == "in":
                return round(num, 3)
            elif unit == "pt":
                return round(num / 72.0, 3)
            return default_in

        top_in = parse_dim_inches(margins.get("top"), 0.8)
        bottom_in = parse_dim_inches(margins.get("bottom"), 0.8)
        left_in = parse_dim_inches(margins.get("left"), 0.6)
        right_in = parse_dim_inches(margins.get("right"), 0.6)

        left_pad = margins.get("left", "15mm")
        right_pad = margins.get("right", "15mm")

        vars_dict = getattr(theme, "variables", {}) or {}

        # Typography & Colors from theme variables
        h_font = vars_dict.get("--page-header-font") or vars_dict.get("--font-sans") or "'Inter', sans-serif"
        h_size = vars_dict.get("--page-header-size", "7.5pt")
        h_color = vars_dict.get("--page-header-color", "#64748b")
        is_cyber = "cyber" in getattr(theme, "name", "").lower()
        is_forensic = "forensic" in getattr(theme, "name", "").lower()
        default_h_border = "1px solid rgba(6, 182, 212, 0.4)" if is_cyber else ("1px solid #cbd5e1" if is_forensic else "none")
        default_f_border = "1px solid rgba(6, 182, 212, 0.25)" if is_cyber else ("1px solid #e2e8f0" if is_forensic else "none")

        h_border = vars_dict.get("--page-header-border", default_h_border)

        f_font = vars_dict.get("--page-footer-font") or vars_dict.get("--font-sans") or "'Inter', sans-serif"
        f_size = vars_dict.get("--page-footer-size", "7.5pt")
        f_color = vars_dict.get("--page-footer-color", "#64748b")
        f_border = vars_dict.get("--page-footer-border", default_f_border)

        # Border styles
        border_bottom_css = f"border-bottom: {h_border}; padding-bottom: 2mm;" if h_border and h_border != "none" else ""
        border_top_css = f"border-top: {f_border}; padding-top: 2mm;" if f_border and f_border != "none" else ""

        badge_color = "#dc2626" if ("restricted" in classification.lower() or "red" in classification.lower()) else ("#06b6d4" if is_cyber else vars_dict.get("--accent", "#475569"))

        header_html = f"""<div class="paged-header-template" style="font-size: {h_size}; font-family: {h_font}; color: {h_color}; width: 100%; display: flex; justify-content: space-between; align-items: center; padding-left: {left_pad}; padding-right: {right_pad}; {border_bottom_css} box-sizing: border-box;">
  <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 40%;">{html.escape(h_left)}</span>
  <span style="font-weight: bold; color: {badge_color}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{html.escape(h_center)}</span>
  <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 40%; text-align: right;">{html.escape(h_right)}</span>
</div>"""

        footer_html = f"""<div class="paged-footer-template" style="font-size: {f_size}; font-family: {f_font}; color: {f_color}; width: 100%; display: flex; justify-content: space-between; align-items: center; padding-left: {left_pad}; padding-right: {right_pad}; {border_top_css} box-sizing: border-box;">
  <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap; max-width: 40%;">{html.escape(f_left)}</span>
  <span style="overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{html.escape(f_center)}</span>
  <span style="white-space: nowrap; text-align: right;">{f_right}</span>
</div>"""

        first_page = paged_cfg.get("first_page", {})

        return {
            "headerTemplate": header_html,
            "footerTemplate": footer_html,
            "showFirstHeader": first_page.get("show_header", True),
            "showFirstFooter": first_page.get("show_footer", True),
            "marginTop": top_in,
            "marginBottom": bottom_in,
            "marginLeft": left_in,
            "marginRight": right_in,
        }
