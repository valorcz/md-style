"""
core/parser/plugins/mermaid.py
Markdown-it-py fence interceptor plugin for Mermaid diagrams.
Intercepts fenced blocks with info starting with 'mermaid' or '{.mermaid' and delegates
rendering to MermaidRenderer without CommonMark indentation mangling.
"""

import re
from typing import Optional
from markdown_it import MarkdownIt
from core.diagrams.mermaid import MermaidRenderer

def mermaid_plugin(
    md: MarkdownIt,
    renderer: Optional[MermaidRenderer] = None,
    theme: str = "zinc-light",
    lang: str = "en"
):
    """Registers fence rule for Mermaid diagrams."""
    orig_fence = md.renderer.rules.get("fence")

    def fence_wrapper(tokens, idx, options, env):
        token = tokens[idx]
        info = token.info.strip() if token.info else ""

        is_mermaid = False
        attrs_str = ""

        if info.startswith("mermaid"):
            is_mermaid = True
            attrs_str = info[len("mermaid"):].strip()
        elif info.startswith("{.mermaid") or info.startswith("{ .mermaid"):
            is_mermaid = True
            attrs_str = info.strip("{}").strip()
            if attrs_str.startswith(".mermaid"):
                attrs_str = attrs_str[len(".mermaid"):].strip()
        elif ".mermaid" in info:
            is_mermaid = True
            attrs_str = info

        if is_mermaid:
            id_attr = ""
            id_m = re.search(r"#([A-Za-z0-9_\-]+)", attrs_str)
            if id_m:
                id_attr = id_m.group(1)

            caption = ""
            cap_m = re.search(r'(?:caption|title)=["\']([^"\']+)["\']', attrs_str)
            if cap_m:
                caption = cap_m.group(1)

            line_no = (token.map[0] + 1) if token.map else None
            doc_lang = env.get("lang", lang) if isinstance(env, dict) else lang
            doc_theme = env.get("theme", theme) if isinstance(env, dict) else theme

            r = renderer or MermaidRenderer()
            html_fig, _ = r.render_figure(
                code=token.content,
                id_attr=id_attr,
                caption=caption,
                lang=doc_lang,
                theme=doc_theme,
                line_no=line_no,
            )
            return html_fig + "\n"

        if orig_fence:
            return orig_fence(tokens, idx, options, env)
        return ""

    md.renderer.rules["fence"] = fence_wrapper
