"""
core/bundler.py
100% self-contained single-file HTML & asset bundler.
Inlines CSS, base64 fonts, base64 images, embedded Knowledge Pack JSON, i18n dictionary,
and pre-compiled Svelte viewer. Zero external network requests required.
"""

import os
import re
import base64
import mimetypes
import json
import html
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.themes import ResolvedTheme
from core.kb.models import KnowledgePack
from core.fonts import FontBundler
from core.icons import IconService
from core.i18n import I18nCatalog
from core.diagnostics import Diagnostics

ASSETS_DIR = Path(__file__).parent / "assets"

class AssetBundler:
    """Bundles HTML fragments, styles, KB data, i18n, fonts, and scripts into a standalone offline HTML document."""

    def __init__(self, doc_path: Path, allow_online: bool = True):
        self.doc_path = doc_path
        self.doc_dir = doc_path.parent
        self.allow_online = allow_online
        self.font_bundler = FontBundler(allow_online=allow_online)
        self.icon_service = IconService(allow_online=allow_online)
        self.fingerprint: str = ""

    def encode_file_base64(self, file_path: Path) -> Optional[str]:
        if not file_path.is_file():
            return None
        mime, _ = mimetypes.guess_type(str(file_path))
        if not mime:
            if file_path.suffix.lower() == ".woff2":
                mime = "font/woff2"
            elif file_path.suffix.lower() == ".woff":
                mime = "font/woff"
            elif file_path.suffix.lower() == ".ttf":
                mime = "font/ttf"
            elif file_path.suffix.lower() == ".svg":
                mime = "image/svg+xml"
            else:
                mime = "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("ascii")
            return f"data:{mime};base64,{encoded}"
        except Exception as e:
            Diagnostics.warn(f"Failed to base64-encode {file_path}: {e}")
            return None

    def inline_images(self, html_content: str) -> str:
        """Finds local img src attributes and replaces them with base64 data URIs."""
        def _repl(match: re.Match) -> str:
            prefix = match.group(1)
            src = match.group(2)
            suffix = match.group(3)

            if src.startswith("data:") or src.startswith("http://") or src.startswith("https://"):
                return match.group(0)

            img_path = (self.doc_dir / src).resolve() if not Path(src).is_absolute() else Path(src)
            data_uri = self.encode_file_base64(img_path)
            if data_uri:
                return f'{prefix}src="{data_uri}"{suffix}'
            return match.group(0)

        img_pattern = re.compile(r'(<img\b[^>]*\b)src=["\']([^"\']+)["\']([^>]*>)', re.IGNORECASE)
        return img_pattern.sub(_repl, html_content)

    def sanitize_inline_styles(self, html_content: str) -> str:
        """
        Finds all <style> blocks in HTML/SVG fragments and sanitizes them against WAN leakage.
        When allow_online=False, strips/replaces all external @import url(...) and remote font URLs.
        When allow_online=True, processes them through FontBundler to inline binary fonts as base64.
        """
        def _repl(match: re.Match) -> str:
            prefix = match.group(1)
            raw_css = match.group(2)
            suffix = match.group(3)

            # Process CSS through FontBundler (resolves @import and inlines/removes remote font URLs)
            processed_css = self.font_bundler.process_css(raw_css, self.doc_dir)

            if not self.allow_online:
                # Defense-in-depth: strip any residual remote @import url(...) (including &amp; variants)
                processed_css = re.sub(
                    r'@import\s+(?:url\([\'"]?https?://[^\'")]+[\'"]?\)|[\'"]https?://[^\'"]+[\'"])[^;]*;?',
                    r'/* Air-gap: stripped remote @import */',
                    processed_css,
                    flags=re.IGNORECASE,
                )
                # Strip any residual remote font URLs
                processed_css = re.sub(
                    r'url\([\'"]?https?://[^\'")]+[\'"]?\)',
                    r'local("")',
                    processed_css,
                    flags=re.IGNORECASE,
                )
            return f"{prefix}{processed_css}{suffix}"

        style_pattern = re.compile(r'(<style\b[^>]*>)(.*?)(</style>)', re.DOTALL | re.IGNORECASE)
        sanitized = style_pattern.sub(_repl, html_content)

        if not self.allow_online:
            # Strip external <link rel="stylesheet"> or WAN preconnects
            sanitized = re.sub(
                r'<link\b[^>]*href=["\']https?://[^"\']+["\'][^>]*>',
                r'<!-- Air-gap: stripped remote link -->',
                sanitized,
                flags=re.IGNORECASE,
            )

        return sanitized

    def resolve_paged_variables(
        self,
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

        import datetime
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

        if h_left: vars_dict["--page-header-left"] = format_css_val(h_left)
        if h_center: vars_dict["--page-header-center"] = format_css_val(h_center)
        if h_right: vars_dict["--page-header-right"] = format_css_val(h_right)

        f_left = interpolate(footers.get("left", ""))
        f_center = interpolate(footers.get("center", ""))
        f_right = interpolate(footers.get("right", ""))

        if f_left: vars_dict["--page-footer-left"] = format_css_val(f_left)
        if f_center: vars_dict["--page-footer-center"] = format_css_val(f_center)
        if f_right: vars_dict["--page-footer-right"] = format_css_val(f_right)

        if not first_page.get("show_header", True):
            vars_dict["--page-first-header-left"] = "none"
            vars_dict["--page-first-header-center"] = "none"
            vars_dict["--page-first-header-right"] = "none"
        if not first_page.get("show_footer", True):
            vars_dict["--page-first-footer-left"] = "none"
            vars_dict["--page-first-footer-center"] = "none"
            vars_dict["--page-first-footer-right"] = "none"

        return vars_dict

    def build_cdp_header_footer_templates(
        self,
        theme: Any,
        catalog: I18nCatalog,
        title: str,
        frontmatter: Optional[Dict[str, Any]] = None,
        fingerprint: str = ""
    ) -> Dict[str, Any]:
        """Synthesizes HTML header and footer templates for native Chromium CDP printing."""
        paged_cfg = getattr(theme, "paged", {}) or {}
        headers = paged_cfg.get("headers", {})
        footers = paged_cfg.get("footers", {})
        margins = paged_cfg.get("margins", {})
        fm = frontmatter or {}

        import datetime
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

        # 1. Typography & Colors from theme variables
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

        # 2. Border styles (only add border line if not 'none')
        border_bottom_css = f"border-bottom: {h_border}; padding-bottom: 2mm;" if h_border and h_border != "none" else ""
        border_top_css = f"border-top: {f_border}; padding-top: 2mm;" if f_border and f_border != "none" else ""

        is_cyber = "cyber" in getattr(theme, "name", "").lower()
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

    def assemble(
        self,
        html_fragment: str,
        theme: ResolvedTheme,
        knowledge_pack: Optional[KnowledgePack] = None,
        catalog: Optional[I18nCatalog] = None,
        title: str = "Report",
        lang: str = "en",
        paged_mode: bool = False,
        print_mode: bool = False,
        frontmatter: Optional[Dict[str, Any]] = None,
        raw_markdown: Optional[str] = None,
        meta_tags: Optional[Dict[str, str]] = None,
        annotations: Optional[List[Dict[str, Any]]] = None
    ) -> str:
        """Assembles a completely self-contained offline HTML file with embedded fonts and i18n."""
        import hashlib
        meta_tags = meta_tags or {}
        catalog = catalog or I18nCatalog(lang)
        frontmatter = frontmatter or {}
        fingerprint = hashlib.sha256(html_fragment.encode("utf-8")).hexdigest()
        self.fingerprint = fingerprint

        # 1. Collect all CSS stylesheets and process through FontBundler
        css_blocks: List[str] = []

        # Resolve paged and i18n variables from theme and document
        paged_vars = self.resolve_paged_variables(theme, catalog, title, frontmatter, fingerprint)
        all_variables = dict(theme.variables)
        all_variables.update(catalog.export_css_variables())
        all_variables.update(paged_vars)

        if all_variables:
            var_lines = [":root {"]
            for k, v in all_variables.items():
                var_name = k if k.startswith("--") else f"--{k}"
                var_lines.append(f"  {var_name}: {v};")
            var_lines.append("}")
            css_blocks.append(f"/* Theme Variables */\n" + "\n".join(var_lines))

        # Theme cascaded stylesheets with font inlining
        for s_path in theme.stylesheet_paths:
            if s_path.is_file():
                try:
                    raw_css = s_path.read_text(encoding="utf-8")
                    processed_css = self.font_bundler.process_css(raw_css, s_path.parent)
                    css_blocks.append(f"/* Stylesheet: {s_path.name} */\n{processed_css}")
                except Exception as e:
                    Diagnostics.warn(f"Failed to read stylesheet {s_path}: {e}")

        # Always include base paged.css and paged-harness.css so paged preview and print are styled
        paged_css_path = Path(__file__).parent.parent / "styles" / "base" / "paged.css"
        if paged_css_path.is_file():
            raw_paged = paged_css_path.read_text(encoding="utf-8")
            css_blocks.append(f"/* Paged.js Styles */\n{raw_paged}")

        paged_harness_path = Path(__file__).parent.parent / "styles" / "base" / "paged-harness.css"
        if paged_harness_path.is_file():
            raw_harness = paged_harness_path.read_text(encoding="utf-8")
            css_blocks.append(f"/* Paged Harness Styles */\n{raw_harness}")

        # Print mode CSS if active
        if print_mode:
            print_css_path = Path(__file__).parent.parent / "styles" / "base" / "print.css"
            if print_css_path.is_file():
                raw_print = print_css_path.read_text(encoding="utf-8")
                css_blocks.append(f"/* Print Styles */\n{raw_print}")

        # Svelte viewer CSS
        enable_interactive = theme.features.get("interactive_viewer", True)
        viewer_css_path = ASSETS_DIR / "viewer.bundle.css"
        if enable_interactive and viewer_css_path.is_file():
            try:
                css_blocks.append(f"/* Svelte Viewer Component Styles */\n{viewer_css_path.read_text(encoding='utf-8')}")
            except Exception:
                pass

        # Pygments Syntax Highlighting CSS
        highlight_style = getattr(theme, "highlight_style", "one-dark") or "one-dark"
        try:
            from pygments.formatters import HtmlFormatter
            syntax_formatter = HtmlFormatter(style=highlight_style, classprefix="tok-")
            syntax_css = syntax_formatter.get_style_defs(".highlight-code")
            css_blocks.append(f"/* Pygments Syntax Highlighting ({highlight_style}) */\n{syntax_css}")
        except Exception as e:
            Diagnostics.warn(f"Failed to generate Pygments CSS for {highlight_style}: {e}")

        # 2. Inline images and sanitize inline styles (including embedded SVGs)
        processed_html = self.inline_images(html_fragment)
        processed_html = self.sanitize_inline_styles(processed_html)

        # 3. Knowledge Pack embedded JSON
        kb_script_block = ""
        if knowledge_pack and knowledge_pack.entities:
            kb_json_str = json.dumps(knowledge_pack.to_dict(), ensure_ascii=False)
            kb_script_block = (
                f'<script id="md-style-kb-data" type="application/json">\n'
                f'{kb_json_str}\n'
                f'</script>\n'
            )

        # 4. Injected i18n dictionary for Svelte viewer
        i18n_ui = catalog.export_ui_dict()
        i18n_json_str = json.dumps(i18n_ui, ensure_ascii=False)
        i18n_script_block = (
            f'<script id="md-style-i18n" type="application/json">\n'
            f'{i18n_json_str}\n'
            f'</script>\n'
        )

        # 5. Embedded Raw Markdown Source (Self-contained archive)
        source_markdown_block = ""
        if raw_markdown:
            safe_md = raw_markdown.replace("</script>", "<\\/script>")
            source_markdown_block = (
                f'<script id="md-style-source-markdown" type="text/markdown">\n'
                f'{safe_md}\n'
                f'</script>\n'
            )

        # 5b. Embedded Annotations (Pre-baked baseline annotations from frontmatter/CLI)
        annotations_data = annotations or frontmatter.get("annotations")
        annotations_script_block = ""
        if annotations_data:
            ann_manifest = {
                "version": "1.0",
                "document_fingerprint": fingerprint,
                "annotations": annotations_data
            }
            ann_json_str = json.dumps(ann_manifest, ensure_ascii=False).replace("<", "\\u003c")
            annotations_script_block = (
                f'<script id="md-style-annotations" type="application/json">\n'
                f'{ann_json_str}\n'
                f'</script>\n'
            )

        # 6. Shared Header & Footer Templates (Single Source of Truth for CDP & Paged.js)
        print_templates = self.build_cdp_header_footer_templates(
            theme=theme,
            catalog=catalog,
            title=title,
            frontmatter=frontmatter,
            fingerprint=fingerprint
        )
        print_templates_json = json.dumps(print_templates, ensure_ascii=False)
        print_templates_block = (
            f'<script id="md-style-print-templates" type="application/json">\n'
            f'{print_templates_json}\n'
            f'</script>\n'
        )

        # 7. Svelte viewer JS bundle
        viewer_script_block = ""
        viewer_js_path = ASSETS_DIR / "viewer.bundle.js"
        if enable_interactive and viewer_js_path.is_file():
            try:
                bundle_code = viewer_js_path.read_text(encoding="utf-8")
                viewer_script_block = (
                    f'<script>\n'
                    f'{bundle_code}\n'
                    f'try {{\n'
                    f'  if (typeof MdStyleViewer !== "undefined" && typeof MdStyleViewer.initViewer === "function") {{\n'
                    f'    MdStyleViewer.initViewer();\n'
                    f'  }}\n'
                    f'}} catch (e) {{ console.error("[Viewer] Initialization failed:", e); }}\n'
                    f'</script>\n'
                )
            except Exception as e:
                Diagnostics.warn(f"Failed to read Svelte viewer bundle: {e}")

        # 8. Build body classes
        body_classes = [f"theme-{theme.name.replace('/', '-')}"]
        if paged_mode:
            body_classes.append("paged-preview")
        if print_mode:
            body_classes.append("print-mode")

        combined_css = "\n\n".join(css_blocks)

        full_html = f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <meta name="doc-title" content="{title}">
  <meta name="doc-fingerprint" content="{fingerprint}">
  <title>{title}</title>
  <style>
{combined_css}
  </style>
</head>
<body class="{' '.join(body_classes)}">
  <main class="report-content">
{processed_html}
  </main>
{kb_script_block}
{i18n_script_block}
{source_markdown_block}
{annotations_script_block}
{print_templates_block}
<div id="md-style-viewer-root"></div>
{viewer_script_block}
</body>
</html>
"""
        return full_html
