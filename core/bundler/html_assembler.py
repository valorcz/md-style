"""
core/bundler/html_assembler.py
Assembles the complete self-contained, offline HTML report document.
"""

import re
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional, List

from core.diagnostics import Diagnostics
from core.themes import ResolvedTheme
from core.kb.models import KnowledgePack
from core.i18n import I18nCatalog
from core.fonts import FontBundler
from core.bundler.paged_resolver import PagedVariableResolver
from core.bundler.cdp_template import CdpTemplateBuilder

ASSETS_DIR = Path(__file__).resolve().parent.parent / "assets"
STYLES_DIR = Path(__file__).resolve().parent.parent.parent / "styles"


class HtmlDocumentBuilder:
    """Assembles all stylesheets, embedded JSON metadata, Svelte viewer JS, and body markup into standalone HTML."""

    def __init__(self, font_bundler: Optional[FontBundler] = None):
        self.font_bundler = font_bundler or FontBundler()

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
        annotations: Optional[List[Dict[str, Any]]] = None,
        interactive_viewer: Optional[bool] = None,
    ) -> str:
        meta_tags = meta_tags or {}
        catalog = catalog or I18nCatalog(lang)
        frontmatter = frontmatter or {}
        fingerprint = hashlib.sha256(html_fragment.encode("utf-8")).hexdigest()

        # Resolve interactive viewer setting
        if interactive_viewer is not None:
            enable_interactive = interactive_viewer
        elif frontmatter and ("interactive_viewer" in frontmatter or "viewer" in frontmatter):
            val = frontmatter.get("interactive_viewer")
            if val is None:
                val = frontmatter.get("viewer")
            if isinstance(val, str):
                enable_interactive = val.strip().lower() not in ("false", "no", "off", "0", "disable", "disabled")
            else:
                enable_interactive = bool(val)
        else:
            enable_interactive = theme.features.get("interactive_viewer", True)

        # 1. Collect all CSS stylesheets and process through FontBundler
        css_blocks: List[str] = []

        # Resolve paged and i18n variables from theme and document
        paged_vars = PagedVariableResolver.resolve_paged_variables(theme, catalog, title, frontmatter, fingerprint)
        all_variables = dict(theme.variables)
        all_variables.update(catalog.export_css_variables())
        all_variables.update(paged_vars)

        if all_variables:
            var_lines = [":root {"]
            for k, v in all_variables.items():
                var_name = k if k.startswith("--") else f"--{k}"
                var_lines.append(f"  {var_name}: {v};")
            var_lines.append("}")
            css_blocks.append("/* Theme Variables */\n" + "\n".join(var_lines))

        # Theme cascaded stylesheets with font inlining
        for s_path in theme.stylesheet_paths:
            if s_path.is_file():
                try:
                    raw_css = s_path.read_text(encoding="utf-8")
                    processed_css = self.font_bundler.process_css(raw_css, s_path.parent)
                    css_blocks.append(f"/* Stylesheet: {s_path.name} */\n{processed_css}")
                except Exception as e:
                    Diagnostics.warn(f"Failed to read stylesheet {s_path}: {e}")

        # Base paged styles
        paged_css_path = STYLES_DIR / "base" / "paged.css"
        if paged_css_path.is_file():
            raw_paged = paged_css_path.read_text(encoding="utf-8")
            css_blocks.append(f"/* Paged.js Styles */\n{raw_paged}")

        paged_harness_path = STYLES_DIR / "base" / "paged-harness.css"
        if paged_harness_path.is_file():
            raw_harness = paged_harness_path.read_text(encoding="utf-8")
            css_blocks.append(f"/* Paged Harness Styles */\n{raw_harness}")

        # Print mode CSS if active
        if print_mode:
            print_css_path = STYLES_DIR / "base" / "print.css"
            if print_css_path.is_file():
                raw_print = print_css_path.read_text(encoding="utf-8")
                css_blocks.append(f"/* Print Styles */\n{raw_print}")

        # Svelte viewer CSS
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

        # Embedded JSON data scripts
        kb_script_block = ""
        if knowledge_pack and knowledge_pack.entities:
            kb_json_str = json.dumps(knowledge_pack.to_dict(), ensure_ascii=False)
            kb_script_block = (
                f'<script id="md-style-kb-data" type="application/json">\n'
                f'{kb_json_str}\n'
                f'</script>\n'
            )

        i18n_ui = catalog.export_ui_dict()
        i18n_json_str = json.dumps(i18n_ui, ensure_ascii=False)
        i18n_script_block = (
            f'<script id="md-style-i18n" type="application/json">\n'
            f'{i18n_json_str}\n'
            f'</script>\n'
        )

        source_markdown_block = ""
        if raw_markdown:
            safe_md = raw_markdown.replace("</script>", "<\\/script>")
            source_markdown_block = (
                f'<script id="md-style-source-markdown" type="text/markdown">\n'
                f'{safe_md}\n'
                f'</script>\n'
            )

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

        print_templates = CdpTemplateBuilder.build(
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

        body_classes = [f"theme-{theme.name.replace('/', '-')}"]
        if paged_mode:
            body_classes.append("paged-preview")
        if print_mode:
            body_classes.append("print-mode")

        combined_css = "\n\n".join(css_blocks)
        meta_tags_html = "\n" + "\n".join(f'  <meta name="{k}" content="{v}">' for k, v in meta_tags.items()) if meta_tags else ""

        return f"""<!DOCTYPE html>
<html lang="{lang}">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">{meta_tags_html}
  <meta name="doc-title" content="{title}">
  <meta name="doc-fingerprint" content="{fingerprint}">
  <title>{title}</title>
  <style>
{combined_css}
  </style>
</head>
<body class="{' '.join(body_classes)}">
<main class="report-content">
{html_fragment}
</main>

{kb_script_block}
{i18n_script_block}
{source_markdown_block}
{annotations_script_block}
{print_templates_block}
{f'<div id="md-style-viewer-root"></div>\n' if enable_interactive else ''}{viewer_script_block}
</body>
</html>
"""


# ---------------------------------------------------------------------------
# Bundled HTML Inspection & De-bundling Utilities
# ---------------------------------------------------------------------------

MD_STYLE_MARKERS = [
    'id="md-style-source-markdown"',
    'id="md-style-kb-data"',
    'id="md-style-viewer-root"',
    'id="md-style-annotations"',
    'name="doc-fingerprint"',
]


def is_md_style_html(path_or_content: Any) -> bool:
    """
    Checks whether a file path or HTML string is an HTML report bundled by md-style.
    Inspects content for distinctive md-style signatures.
    """
    content = ""
    if isinstance(path_or_content, Path):
        if not path_or_content.exists() or not path_or_content.is_file():
            return False
        try:
            with open(path_or_content, "r", encoding="utf-8", errors="ignore") as f:
                content = f.read(131072)
        except Exception:
            return False
    else:
        content = str(path_or_content)[:131072]

    # Quick check in first 128KB
    if any(m in content for m in MD_STYLE_MARKERS):
        return True

    # If file is larger, script tags are positioned near the end of body; check tail
    if isinstance(path_or_content, Path):
        try:
            file_size = path_or_content.stat().st_size
            if file_size > 131072:
                with open(path_or_content, "r", encoding="utf-8", errors="ignore") as f:
                    f.seek(max(0, file_size - 131072))
                    tail = f.read()
                    if any(m in tail for m in MD_STYLE_MARKERS):
                        return True
        except Exception:
            pass

    return False


def extract_bundled_markdown(path_or_content: Any) -> Optional[str]:
    """
    Extracts the original Markdown source embedded inside an md-style bundled HTML report.
    Returns None if the file is not an md-style bundle or if --no-embed-source was used.
    """
    content = ""
    if isinstance(path_or_content, Path):
        if not path_or_content.exists() or not path_or_content.is_file():
            return None
        try:
            content = path_or_content.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None
    else:
        content = str(path_or_content)

    match = re.search(
        r'<script\s+id=["\']md-style-source-markdown["\']\s+type=["\']text/markdown["\']>\s*(.*?)\s*</script>',
        content,
        re.DOTALL
    )
    if not match:
        return None

    extracted = match.group(1)
    # Unescape </script> tag
    extracted = extracted.replace(r"<\/script>", "</script>")
    return extracted.strip()


def extract_bundled_knowledge_pack(path_or_content: Any) -> Optional[Dict[str, Any]]:
    """
    Extracts the Knowledge Pack JSON data embedded inside an md-style bundled HTML report.
    Returns None if not found or if JSON parsing fails.
    """
    content = ""
    if isinstance(path_or_content, Path):
        if not path_or_content.exists() or not path_or_content.is_file():
            return None
        try:
            content = path_or_content.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return None
    else:
        content = str(path_or_content)

    match = re.search(
        r'<script\s+id=["\']md-style-kb-data["\']\s+type=["\']application/json["\']>\s*(.*?)\s*</script>',
        content,
        re.DOTALL
    )
    if not match:
        return None

    try:
        return json.loads(match.group(1).strip())
    except Exception:
        return None


def compute_bundle_size_breakdown(path_or_content: Any) -> Dict[str, int]:
    """
    Computes a size breakdown of a bundled HTML document into component bytes:
    - total: overall document size in bytes (UTF-8)
    - fonts: embedded base64 WOFF2/TTF font data (in stylesheets and diagrams)
    - viewer_js: interactive Svelte viewer bundle code
    - css: stylesheets and style blocks (excluding embedded font data)
    - metadata: embedded JSON/markdown scripts (KB, i18n, annotations, print templates, markdown source)
    - diagrams: SVG diagrams in document body (excluding embedded font data)
    - images: embedded base64 images in document body
    - content: document prose markup, tables, headings, callouts
    """
    if isinstance(path_or_content, Path):
        if not path_or_content.is_file():
            return {"total": 0, "fonts": 0, "viewer_js": 0, "css": 0, "metadata": 0, "diagrams": 0, "images": 0, "content": 0}
        try:
            content = path_or_content.read_text(encoding="utf-8", errors="replace")
        except Exception:
            return {"total": 0, "fonts": 0, "viewer_js": 0, "css": 0, "metadata": 0, "diagrams": 0, "images": 0, "content": 0}
    else:
        content = str(path_or_content)

    total = len(content.encode("utf-8"))
    if total == 0:
        return {"total": 0, "fonts": 0, "viewer_js": 0, "css": 0, "metadata": 0, "diagrams": 0, "images": 0, "content": 0}

    # 1. Fonts (data:font/...) across document stylesheets and SVG diagrams
    fonts_bytes = 0
    font_markers = ("data:font/", "data:application/font-", "data:application/x-font-")
    for marker in font_markers:
        idx = 0
        while True:
            pos = content.find(marker, idx)
            if pos == -1:
                break
            end_s = content.find("'", pos)
            end_d = content.find('"', pos)
            end_p = content.find(')', pos)
            ends = [e for e in (end_s, end_d, end_p) if e != -1]
            if not ends:
                break
            end = min(ends)
            fonts_bytes += len(content[pos:end].encode("utf-8"))
            idx = end

    # 2. Svelte viewer JS bundle
    viewer_match = re.search(r'<script[^>]*>\s*([^\n<]*MdStyleViewer[\s\S]*?initViewer[\s\S]*?)</script>', content)
    viewer_bytes = len(viewer_match.group(0).encode("utf-8")) if viewer_match else 0

    # 3. CSS blocks (<style>...</style>) in head minus embedded fonts in head
    head_match = re.search(r'<head[^>]*>([\s\S]*?)</head>', content)
    head_content = head_match.group(1) if head_match else ""
    head_css = sum(len(m.group(0).encode("utf-8")) for m in re.finditer(r'<style[^>]*>([\s\S]*?)</style>', head_content))
    fonts_in_head = 0
    for marker in font_markers:
        idx = 0
        while True:
            pos = head_content.find(marker, idx)
            if pos == -1:
                break
            end_s = head_content.find("'", pos)
            end_d = head_content.find('"', pos)
            end_p = head_content.find(')', pos)
            ends = [e for e in (end_s, end_d, end_p) if e != -1]
            if not ends:
                break
            end = min(ends)
            fonts_in_head += len(head_content[pos:end].encode("utf-8"))
            idx = end
    css_bytes = max(0, head_css - fonts_in_head)

    # 4. Metadata scripts (KB, i18n, markdown source, annotations, print templates)
    meta_bytes = sum(len(m.group(0).encode("utf-8")) for m in re.finditer(r'<script[^>]*id=["\'](md-style-[^"\']+)["\'][^>]*>([\s\S]*?)</script>', content))

    # 5. Inside document body (<main class="report-content">):
    main_match = re.search(r'<main[^>]*>([\s\S]*?)</main>', content)
    main_content = main_match.group(1) if main_match else ""

    # SVGs (Mermaid, D2, vector figures) inside main minus fonts inside SVGs
    svg_matches = list(re.finditer(r'<svg[\s\S]*?</svg>', main_content))
    raw_svg_bytes = sum(len(m.group(0).encode("utf-8")) for m in svg_matches)
    fonts_in_svg = 0
    for sm in svg_matches:
        s_text = sm.group(0)
        for marker in font_markers:
            idx = 0
            while True:
                pos = s_text.find(marker, idx)
                if pos == -1:
                    break
                end_s = s_text.find("'", pos)
                end_d = s_text.find('"', pos)
                end_p = s_text.find(')', pos)
                ends = [e for e in (end_s, end_d, end_p) if e != -1]
                if not ends:
                    break
                end = min(ends)
                fonts_in_svg += len(s_text[pos:end].encode("utf-8"))
                idx = end
    diagram_bytes = max(0, raw_svg_bytes - fonts_in_svg)

    # Embedded base64 images inside main
    img_bytes = sum(len(m.group(0).encode("utf-8")) for m in re.finditer(r'src=["\']data:image/[^;]+;base64,[A-Za-z0-9+/=]+["\']', main_content))

    # 6. Markup & text (HTML structure, tables, callouts, headings, prose)
    content_bytes = max(0, total - fonts_bytes - viewer_bytes - css_bytes - meta_bytes - diagram_bytes - img_bytes)

    return {
        "total": total,
        "fonts": fonts_bytes,
        "viewer_js": viewer_bytes,
        "css": css_bytes,
        "metadata": meta_bytes,
        "diagrams": diagram_bytes,
        "images": img_bytes,
        "content": content_bytes,
    }


def format_bundle_size_breakdown(breakdown: Dict[str, int]) -> str:
    """Formats the size breakdown dictionary into a structured Rich markup string."""
    tot = breakdown.get("total", 0)
    if tot <= 0:
        return ""

    def _fmt(b: int) -> str:
        if b >= 1024 * 1024:
            return f"{b / (1024 * 1024):.1f} MB"
        return f"{b / 1024:.0f} KB" if b >= 1024 else f"{b} B"

    f_bytes = breakdown.get("fonts", 0)
    v_bytes = breakdown.get("viewer_js", 0)
    c_bytes = breakdown.get("css", 0)
    m_bytes = breakdown.get("metadata", 0)
    d_bytes = breakdown.get("diagrams", 0)
    img_bytes = breakdown.get("images", 0)
    cnt_bytes = breakdown.get("content", 0)

    line1_parts = []
    if f_bytes > 0:
        f_pct = f_bytes / tot * 100
        line1_parts.append(f"[dim]Fonts:[/dim] [white]{_fmt(f_bytes)}[/white] [dim]({f_pct:.0f}%)[/dim]")
    if v_bytes > 0:
        v_pct = v_bytes / tot * 100
        line1_parts.append(f"[dim]Viewer JS:[/dim] [white]{_fmt(v_bytes)}[/white] [dim]({v_pct:.0f}%)[/dim]")

    line2_parts = []
    if c_bytes > 0:
        line2_parts.append(f"[dim]CSS:[/dim] [white]{_fmt(c_bytes)}[/white]")
    if m_bytes > 0:
        line2_parts.append(f"[dim]Data:[/dim] [white]{_fmt(m_bytes)}[/white]")

    line3_parts = []
    if d_bytes > 0:
        line3_parts.append(f"[dim]Diagrams:[/dim] [white]{_fmt(d_bytes)}[/white]")
    if img_bytes > 0:
        line3_parts.append(f"[dim]Images:[/dim] [white]{_fmt(img_bytes)}[/white]")
    if cnt_bytes > 0:
        lbl = "Markup:" if (d_bytes > 0 or img_bytes > 0) else "Content:"
        line3_parts.append(f"[dim]{lbl}[/dim] [white]{_fmt(cnt_bytes)}[/white]")

    lines = []
    if line1_parts:
        lines.append(" [dim]•[/dim] ".join(line1_parts))
    if line2_parts and not (d_bytes > 0 or img_bytes > 0):
        line2_parts.extend(line3_parts)
        lines.append(" [dim]•[/dim] ".join(line2_parts))
    else:
        if line2_parts:
            lines.append(" [dim]•[/dim] ".join(line2_parts))
        if line3_parts:
            lines.append(" [dim]•[/dim] ".join(line3_parts))

    return "\n".join(lines)


