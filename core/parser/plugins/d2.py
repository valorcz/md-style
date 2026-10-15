"""
core/parser/plugins/d2.py
Markdown-it-py fence interceptor plugin for D2 diagrams.
Intercepts fenced blocks with info starting with 'd2' or '{.d2' and delegates
rendering to D2Renderer without CommonMark indentation mangling.
"""

import re
from typing import Optional
from markdown_it import MarkdownIt
from core.diagrams.d2 import D2Renderer


def d2_plugin(
    md: MarkdownIt,
    renderer: Optional[D2Renderer] = None,
    theme: str = "base",
    lang: str = "en"
):
    """Registers fence rule for D2 diagrams."""
    orig_fence = md.renderer.rules.get("fence")

    def fence_wrapper(tokens, idx, options, env):
        token = tokens[idx]
        info = token.info.strip() if token.info else ""

        is_d2 = False
        attrs_str = ""

        if info.startswith("d2"):
            # Ensure it's not a word starting with d2, like d2something
            remainder = info[2:].strip()
            if not remainder or remainder.startswith("{") or remainder.startswith("#") or remainder.startswith(".") or remainder.startswith(" "):
                is_d2 = True
                attrs_str = remainder
        elif info.startswith("{.d2") or info.startswith("{ .d2"):
            is_d2 = True
            attrs_str = info.strip("{}").strip()
            if attrs_str.startswith(".d2"):
                attrs_str = attrs_str[len(".d2"):].strip()
        elif ".d2" in info:
            is_d2 = True
            attrs_str = info

        if is_d2:
            id_attr = ""
            id_m = re.search(r"#([A-Za-z0-9_\-]+)", attrs_str)
            if id_m:
                id_attr = id_m.group(1)

            caption = ""
            cap_m = re.search(r'(?:caption|title)=["\']([^"\']+)["\']', attrs_str)
            if cap_m:
                caption = cap_m.group(1)

            sketch = "sketch" in attrs_str.lower()
            line_no = (token.map[0] + 1) if token.map else None
            doc_lang = env.get("lang", lang) if isinstance(env, dict) else lang
            doc_theme = env.get("theme", theme) if isinstance(env, dict) else theme

            r = renderer or D2Renderer()
            html_fig, _ = r.render_figure(
                code=token.content,
                id_attr=id_attr,
                caption=caption,
                lang=doc_lang,
                theme=doc_theme,
                sketch=sketch,
                line_no=line_no,
            )
            return html_fig + "\n"

        if orig_fence:
            return orig_fence(tokens, idx, options, env)
        return ""

    md.renderer.rules["fence"] = fence_wrapper
