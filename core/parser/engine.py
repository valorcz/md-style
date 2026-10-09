"""
core/parser/engine.py
Pure-Python Markdown parsing engine using markdown-it-py, mdit-py-plugins, and Pygments.
Integrates native plugins for Pandoc fenced divs, bracketed spans, callouts, and TOC inlining.
"""

import html
from typing import Dict, Any, List, Tuple, Optional
import yaml

from markdown_it import MarkdownIt
from mdit_py_plugins.front_matter import front_matter_plugin
from mdit_py_plugins.tasklists import tasklists_plugin
from mdit_py_plugins.attrs import attrs_plugin

import pygments
from pygments.lexers import get_lexer_by_name, TextLexer
from pygments.formatters import HtmlFormatter

from core.kb.models import KnowledgePack
from core.i18n import I18nCatalog
from core.icons import IconService
from core.diagrams.mermaid import MermaidRenderer
from core.parser.plugins import pandoc_divs_plugin, callouts_plugin, inline_toc, mermaid_plugin
from core.parser.transforms import (
    transform_tables,
    transform_headings_and_extract_toc,
    transform_entities,
)
from core.diagnostics import Diagnostics

LANG_ALIASES: Dict[str, str] = {
    "hex": "hexdump",
    "ps1": "powershell",
    "posh": "powershell",
    "sh": "bash",
    "shell": "bash",
    "zsh": "bash",
    "yml": "yaml",
    "js": "javascript",
    "ts": "typescript",
    "py": "python",
}

def make_pygments_highlighter(style_name: str = "one-dark"):
    """Creates a Pygments syntax highlighter with language aliases and custom classes."""
    def highlighter(code: str, lang: str, attrs: str) -> str:
        lexer = None
        raw_lang = lang.strip().lower() if lang else ""
        norm_lang = LANG_ALIASES.get(raw_lang, raw_lang)
        if norm_lang:
            try:
                lexer = get_lexer_by_name(norm_lang)
            except Exception:
                lexer = None
        if not lexer:
            lexer = TextLexer()

        formatter = HtmlFormatter(nowrap=True, classprefix="tok-", style=style_name)
        display_lang = html.escape(raw_lang or "text")
        try:
            highlighted = pygments.highlight(code, lexer, formatter)
            return f'<pre class="highlight-code" data-lang="{display_lang}"><code class="language-{display_lang}">{highlighted}</code></pre>'
        except Exception:
            return f'<pre class="highlight-code" data-lang="{display_lang}"><code>{html.escape(code)}</code></pre>'
    return highlighter

def pygments_highlight(code: str, lang: str, attrs: str = "") -> str:
    """Default module-level Pygments highlighter."""
    return make_pygments_highlighter("one-dark")(code, lang, attrs)

class MarkdownParser:
    """Configures and runs pure-Python Markdown compilation pipeline."""

    def __init__(
        self,
        lang: str = "en",
        catalog: Optional[I18nCatalog] = None,
        icon_service: Optional[IconService] = None,
        highlight_style: str = "one-dark",
        enable_toc: bool = True,
        toc_depth: int = 3,
        toc_levels: Optional[List[int]] = None,
        style_family: Optional[str] = None,
        enable_mermaid: bool = True,
        theme_name: str = "zinc-light",
    ):
        self.lang = lang
        self.catalog = catalog or I18nCatalog(lang)
        self.icon_service = icon_service or IconService()
        self.highlight_style = highlight_style
        self.enable_toc = enable_toc
        self.toc_depth = toc_depth
        self.toc_levels = toc_levels
        self.style_family = style_family
        self.enable_mermaid = enable_mermaid
        self.theme_name = theme_name
        self.mermaid_renderer = MermaidRenderer() if enable_mermaid else None

        self.md = (
            MarkdownIt("gfm-like", {
                "html": True,
                "linkify": True,
                "typographer": True,
                "highlight": make_pygments_highlighter(self.highlight_style),
            })
            .use(front_matter_plugin)
            .use(tasklists_plugin)
            .use(attrs_plugin, spans=True)
            .use(pandoc_divs_plugin)
            .use(callouts_plugin, catalog=self.catalog, icon_service=self.icon_service)
            .enable("table")
            .enable("strikethrough")
        )

        if self.enable_mermaid and self.mermaid_renderer:
            self.md.use(
                mermaid_plugin,
                renderer=self.mermaid_renderer,
                theme=self.theme_name,
                lang=self.lang,
            )

    def parse_frontmatter(self, src: str) -> Tuple[str, Dict[str, Any]]:
        """Extracts YAML frontmatter if present and returns (clean_markdown, metadata)."""
        meta: Dict[str, Any] = {}
        cleaned_src = src
        if src.startswith("---"):
            parts = src.split("---", 2)
            if len(parts) >= 3:
                fm_raw = parts[1]
                cleaned_src = parts[2].lstrip()
                try:
                    loaded = yaml.safe_load(fm_raw)
                    if isinstance(loaded, dict):
                        meta = loaded
                except Exception as e:
                    Diagnostics.warn(f"Failed to parse frontmatter: {e}")
        return cleaned_src, meta

    def render(
        self,
        src: str,
        knowledge_pack: Optional[KnowledgePack] = None,
        frontmatter: Optional[Dict[str, Any]] = None
    ) -> Tuple[str, List[Dict[str, Any]], Dict[str, Any]]:
        """
        Parses Markdown, runs transforms, and renders HTML.
        Returns: (html_fragment, toc_list, metadata)
        """
        content, fm_from_src = self.parse_frontmatter(src)
        meta = dict(fm_from_src)
        if frontmatter:
            meta.update(frontmatter)

        # 1. Parse into Token stream (frontmatter, tasklists, spans, callouts, divs)
        env: Dict[str, Any] = {"lang": self.lang, "theme": self.theme_name}
        tokens = self.md.parse(content, env)

        # 2. Run Table transform (<wbr> in timestamp ranges, wrappers, alignments)
        tokens = transform_tables(tokens)

        # 3. Run Headings and TOC transform (anchors & slugification)
        tokens, toc = transform_headings_and_extract_toc(tokens)

        # 4. Inline Table of Contents into placeholder [[TOC]] / ::: {#toc} or top of document
        tokens = inline_toc(
            tokens,
            toc,
            enabled=self.enable_toc,
            max_depth=self.toc_depth,
            catalog=self.catalog,
            levels=self.toc_levels,
            style_family=self.style_family
        )

        # 5. Run Inspectable Entities transform if KnowledgePack is provided
        if knowledge_pack and knowledge_pack.entities:
            tokens = transform_entities(tokens, knowledge_pack)

        # 6. Render tokens to semantic HTML
        html_fragment = self.md.renderer.render(tokens, self.md.options, env)

        return html_fragment, toc, meta
