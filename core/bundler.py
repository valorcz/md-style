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
from pathlib import Path
from typing import List, Dict, Any, Optional

from core.themes import ResolvedTheme
from core.kb.models import KnowledgePack
from core.fonts import FontBundler
from core.i18n import I18nCatalog
from core.diagnostics import Diagnostics

ASSETS_DIR = Path(__file__).parent / "assets"

class AssetBundler:
    """Bundles HTML fragments, styles, KB data, i18n, fonts, and scripts into a standalone offline HTML document."""

    def __init__(self, doc_path: Path):
        self.doc_path = doc_path
        self.doc_dir = doc_path.parent
        self.font_bundler = FontBundler()

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
        meta_tags: Optional[Dict[str, str]] = None
    ) -> str:
        """Assembles a completely self-contained offline HTML file with embedded fonts and i18n."""
        import hashlib
        meta_tags = meta_tags or {}
        catalog = catalog or I18nCatalog(lang)
        frontmatter = frontmatter or {}
        fingerprint = hashlib.sha256(html_fragment.encode("utf-8")).hexdigest()

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

        # Always include base paged.css so paged preview and print are styled
        paged_css_path = Path(__file__).parent.parent / "styles" / "base" / "paged.css"
        if paged_css_path.is_file():
            raw_paged = paged_css_path.read_text(encoding="utf-8")
            css_blocks.append(f"/* Paged.js Styles */\n{raw_paged}")

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

        # 2. Inline images
        processed_html = self.inline_images(html_fragment)

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

        # 6. Svelte viewer JS bundle
        viewer_script_block = ""
        viewer_js_path = ASSETS_DIR / "viewer.bundle.js"
        if enable_interactive and viewer_js_path.is_file():
            try:
                bundle_code = viewer_js_path.read_text(encoding="utf-8")
                viewer_script_block = (
                    f'<script>\n'
                    f'{bundle_code}\n'
                    f'</script>\n'
                )
            except Exception as e:
                Diagnostics.warn(f"Failed to read Svelte viewer bundle: {e}")

        # 7. Build body classes
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
  <title>{title}</title>
  <style>
{combined_css}
  </style>
</head>
<body class="{' '.join(body_classes)}">
  <div id="md-style-viewer-root"></div>
  <main class="report-content">
{processed_html}
  </main>
{kb_script_block}
{i18n_script_block}
{source_markdown_block}
{viewer_script_block}
</body>
</html>
"""
        return full_html
