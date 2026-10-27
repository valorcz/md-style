"""
core/bundler/__init__.py
Modular asset bundling and HTML packaging package.
"""

import re
import hashlib
from pathlib import Path
from typing import Optional, List, Dict, Any, Tuple

from core.themes import ResolvedTheme
from core.kb.models import KnowledgePack
from core.fonts import FontBundler
from core.icons import IconService
from core.i18n import I18nCatalog
from core.diagnostics import Diagnostics
from core.svg import SVGProcessor

from core.bundler.resolver import AssetResolver
from core.bundler.paged_resolver import PagedVariableResolver
from core.bundler.cdp_template import CdpTemplateBuilder
from core.bundler.html_assembler import (
    HtmlDocumentBuilder,
    MD_STYLE_MARKERS,
    is_md_style_html,
    extract_bundled_markdown,
    extract_bundled_knowledge_pack,
)


class AssetBundler:
    """Coordinates asset resolution, SVG inlining, font bundling, and single-file HTML assembly."""

    def __init__(self, doc_path: Path, allow_online: bool = True):
        self.doc_path = doc_path
        self.doc_dir = doc_path.parent if doc_path.is_file() else doc_path
        self.allow_online = allow_online
        self.font_bundler = FontBundler(allow_online=allow_online)
        self.resolver = AssetResolver(self.doc_dir)
        self.html_builder = HtmlDocumentBuilder(self.font_bundler)
        self.fingerprint = ""

    def encode_file_base64(self, file_path: Path) -> Optional[str]:
        return self.resolver.encode_file_base64(file_path)

    def resolve_asset_path(self, src: str) -> Tuple[Optional[Path], List[Path]]:
        return self.resolver.resolve_asset_path(src)

    def inline_images(self, html_content: str) -> str:
        """Finds local img tags and:

        - Inlines vector SVGs directly into the DOM as sanitized, font-bundled <svg> elements.
        - Inlines bitmap images (PNG, JPG, WebP) as base64 data URIs in <img src="...">.
        - Resolves relative asset paths across doc_dir, parent dir, and cwd.
        - Emits build-time warnings for missing or unresolvable assets.
        """
        svg_processor = SVGProcessor(allow_online=self.allow_online)
        svg_index = 0

        def _repl(match: re.Match) -> str:
            nonlocal svg_index
            full_img_tag = match.group(0)
            prefix = match.group(1)
            src = match.group(2)
            suffix = match.group(3)

            if src.startswith("data:") or src.startswith("http://") or src.startswith("https://"):
                return full_img_tag

            img_path, candidates = self.resolve_asset_path(src)
            if not img_path:
                checked_str = "\n".join(f"    - {c}" for c in candidates)
                Diagnostics.warn(
                    f"Referenced image '{src}' could not be resolved on disk.\n"
                    f"  Checked locations:\n{checked_str}"
                )
                return full_img_tag

            # Check if this is an SVG vector graphic for DOM inlining
            if img_path.suffix.lower() == ".svg":
                try:
                    svg_raw = img_path.read_text(encoding="utf-8")
                    svg_index += 1
                    file_hash = hashlib.sha256(str(img_path).encode("utf-8")).hexdigest()[:6]
                    scope_id = f"fig_svg_{svg_index}_{file_hash}"

                    processed_svg, ok = svg_processor.process(
                        svg_raw,
                        prefix=f"pfx_{scope_id}",
                        scope_id=scope_id,
                        source_label=src
                    )

                    if ok:
                        def _bundle_svg_fonts(sm: re.Match) -> str:
                            stag_open, s_body, stag_close = sm.groups()
                            b_css = self.font_bundler.process_css(s_body, img_path.parent)
                            return f"{stag_open}{b_css}{stag_close}"

                        processed_svg = re.compile(
                            r"(<style\b[^>]*>)(.*?)(</style>)",
                            re.DOTALL | re.IGNORECASE
                        ).sub(_bundle_svg_fonts, processed_svg)

                        # Transfer explicit width or style attributes from <img> to inlined wrapper
                        img_style_m = re.search(r'style=["\']([^"\']+)["\']', full_img_tag, re.IGNORECASE)
                        img_width_m = re.search(r'width=["\']([^"\']+)["\']', full_img_tag, re.IGNORECASE)

                        wrapper_styles = []
                        if img_width_m:
                            w_val = img_width_m.group(1).strip()
                            w_css = f"{w_val}px" if w_val.isdigit() else w_val
                            wrapper_styles.append(f"max-width: {w_css};")
                        if img_style_m:
                            wrapper_styles.append(img_style_m.group(1).strip())

                        style_attr = f' style="{" ".join(wrapper_styles)}"' if wrapper_styles else ""
                        return f'<div class="svg-inlined-wrapper"{style_attr}>{processed_svg}</div>'
                    else:
                        Diagnostics.warn(f"Failed to process SVG '{src}' for DOM inlining; falling back to base64 <img>.")
                except Exception as ex:
                    Diagnostics.warn(f"Error reading/processing SVG '{img_path}': {ex}")

            # Non-SVG or SVG fallback: base64 data URI in <img> tag
            data_uri = self.encode_file_base64(img_path)
            if data_uri:
                return f'{prefix}src="{data_uri}"{suffix}'
            return full_img_tag

        img_pattern = re.compile(r'(<img\b[^>]*\b)src=["\']([^"\']+)["\']([^>]*>)', re.IGNORECASE)
        return img_pattern.sub(_repl, html_content)

    def sanitize_inline_styles(self, html_content: str) -> str:
        """Sanitizes all <style> blocks in HTML/SVG fragments against WAN leakage."""
        def _repl(match: re.Match) -> str:
            prefix = match.group(1)
            raw_css = match.group(2)
            suffix = match.group(3)

            processed_css = self.font_bundler.process_css(raw_css, self.doc_dir)

            if not self.allow_online:
                processed_css = re.sub(
                    r'@import\s+(?:url\([\'"]?https?://[^\'")]+[\'"]?\)|[\'"]https?://[^\'"]+[\'"])[^;]*;?',
                    r'/* Air-gap: stripped remote @import */',
                    processed_css,
                    flags=re.IGNORECASE,
                )
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
        return PagedVariableResolver.resolve_paged_variables(
            theme=theme,
            catalog=catalog,
            title=title,
            frontmatter=frontmatter,
            fingerprint=fingerprint or self.fingerprint
        )

    def build_cdp_header_footer_templates(
        self,
        theme: Any,
        catalog: I18nCatalog,
        title: str,
        frontmatter: Optional[Dict[str, Any]] = None,
        fingerprint: str = ""
    ) -> Dict[str, Any]:
        return CdpTemplateBuilder.build(
            theme=theme,
            catalog=catalog,
            title=title,
            frontmatter=frontmatter,
            fingerprint=fingerprint or self.fingerprint
        )

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
        # Pre-process inline images and sanitize styles
        processed_html = self.inline_images(html_fragment)
        processed_html = self.sanitize_inline_styles(processed_html)

        self.fingerprint = hashlib.sha256(processed_html.encode("utf-8")).hexdigest()

        return self.html_builder.assemble(
            html_fragment=processed_html,
            theme=theme,
            knowledge_pack=knowledge_pack,
            catalog=catalog,
            title=title,
            lang=lang,
            paged_mode=paged_mode,
            print_mode=print_mode,
            frontmatter=frontmatter,
            raw_markdown=raw_markdown,
            meta_tags=meta_tags,
            annotations=annotations,
            interactive_viewer=interactive_viewer,
        )


__all__ = [
    "AssetBundler",
    "AssetResolver",
    "PagedVariableResolver",
    "CdpTemplateBuilder",
    "HtmlDocumentBuilder",
    "MD_STYLE_MARKERS",
    "is_md_style_html",
    "extract_bundled_markdown",
    "extract_bundled_knowledge_pack",
]
