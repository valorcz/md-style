"""
core/parser/plugins/pandoc_divs.py
Generic fenced container plugin for markdown-it-py supporting Pandoc-style div syntax:
  ::: {.kpi-grid}
  ::: {#toc}
  ::: {.ai-insight confidence="99.4%" agent="SENTINEL-9"}
  ::: memo-meta-value
Supports nested containers with variable colon lengths (:::: and :::).
"""

import re
import html
from typing import Tuple, List, Dict
from markdown_it import MarkdownIt
from mdit_py_plugins.container import container_plugin

CALLOUT_KEYWORDS = {
    "note", "info", "tip", "success", "important", "warning",
    "caution", "critical", "danger", "evidence", "finding", "proposal"
}

def parse_pandoc_attrs(info_str: str) -> Tuple[str, List[str], Dict[str, str]]:
    """Parses Pandoc style attribute string: {.class #id key=val} or word list."""
    info = info_str.strip()
    elem_id = ""
    classes: List[str] = []
    attrs: Dict[str, str] = {}

    if info.startswith("{") and info.endswith("}"):
        inner = info[1:-1].strip()
        id_m = re.search(r"#([^\s}]+)", inner)
        if id_m:
            elem_id = id_m.group(1)
        clean_inner = re.sub(r"#[^\s}]+", "", inner)

        # Extract key=val, key="val", or key='val'
        kv_pattern = re.compile(r'(\w+)=(?:"([^"]*)"|\'([^\']*)\'|(\S+))')
        for k, v1, v2, v3 in kv_pattern.findall(clean_inner):
            attrs[k] = v1 or v2 or v3 or ""

        # Remove key=val from string to parse standalone classes
        clean_no_kv = kv_pattern.sub("", clean_inner)
        for c in re.findall(r"\.([^\s}]+)", clean_no_kv):
            classes.append(c)
    elif info:
        classes = info.split()

    return elem_id, classes, attrs

def validate_div(params: str, *args) -> bool:
    """Validates if block is a custom div and not a reserved callout keyword."""
    first = params.strip().split()[0] if params.strip() else ""
    first_clean = first.lstrip("{").lstrip(".").rstrip("}").lower()
    return first_clean not in CALLOUT_KEYWORDS

def render_div(self, tokens, idx, _options, env) -> str:
    """Renders opening and closing div tags with parsed attributes."""
    tok = tokens[idx]
    if tok.nesting == 1:
        elem_id, classes, attrs = parse_pandoc_attrs(tok.info)
        parts: List[str] = []
        if elem_id:
            parts.append(f'id="{html.escape(elem_id)}"')
        if classes:
            parts.append(f'class="{html.escape(" ".join(classes))}"')
        for k, v in attrs.items():
            parts.append(f'{html.escape(k)}="{html.escape(v)}"')
        attr_str = (" " + " ".join(parts)) if parts else ""
        return f"<div{attr_str}>\n"
    else:
        return "</div>\n"

def pandoc_divs_plugin(md: MarkdownIt) -> None:
    """Registers generic pandoc fenced container plugin."""
    md.use(container_plugin, name="pandoc_div", validate=validate_div, render=render_div)
