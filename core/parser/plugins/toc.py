"""
core/parser/plugins/toc.py
Table of Contents (TOC) rendering and inlining plugin.
Supports:
  1. Explicit placeholder replacement: [[TOC]], [TOC], or ::: {#toc}
  2. Automatic document-level inlining when enabled=True and no placeholder exists.
"""

import re
import html
from typing import List, Dict, Any, Optional
from markdown_it.token import Token
from core.i18n import I18nCatalog

def parse_toc_attributes(info: str, content: str = "") -> Dict[str, Any]:
    """Parses attributes from {#toc ...} info string or content."""
    text = f"{info} {content}"
    attrs: Dict[str, Any] = {}
    sec_m = re.search(r'(?:section|from|root)=["\']([^"\']+)["\']', text, re.IGNORECASE)
    if sec_m:
        attrs["section"] = sec_m.group(1).strip()
    lvl_m = re.search(r'levels=["\']([^"\']+)["\']', text, re.IGNORECASE)
    if lvl_m:
        try:
            attrs["levels"] = [int(x.strip()) for x in lvl_m.group(1).split(",") if x.strip().isdigit()]
        except Exception:
            pass
    title_m = re.search(r'title=["\']([^"\']+)["\']', text, re.IGNORECASE)
    if title_m:
        attrs["title"] = title_m.group(1).strip()
    return attrs

def filter_toc_by_section(toc_items: List[Dict[str, Any]], section_name: str) -> List[Dict[str, Any]]:
    """Filters TOC items to only include subheadings under the specified section heading."""
    clean_target = section_name.strip().lower()
    target_idx = None
    target_level = None

    for idx, it in enumerate(toc_items):
        it_title = it.get("title", "").strip().lower()
        it_id = it.get("id", "").strip().lower()
        if clean_target in it_title or clean_target in it_id:
            target_idx = idx
            target_level = it.get("level", 1)
            break

    if target_idx is None:
        return []

    sub_items = []
    for it in toc_items[target_idx + 1:]:
        if it.get("level", 1) <= target_level:
            break
        sub_items.append(it)

    return sub_items

def render_toc_html(
    toc_items: List[Dict[str, Any]],
    catalog: Optional[I18nCatalog] = None,
    max_depth: int = 3,
    levels: Optional[List[int]] = None,
    style_family: Optional[str] = None,
    section: Optional[str] = None,
    title_override: Optional[str] = None
) -> str:
    """Renders structured semantic TOC or SVJ agenda card."""
    catalog = catalog or I18nCatalog("en")

    # If section is requested, filter down to subheadings under that section
    items_to_render = toc_items
    if section:
        extracted = filter_toc_by_section(toc_items, section)
        if extracted:
            items_to_render = extracted
    elif style_family and "svj" in style_family.lower():
        # SVJ default heuristic: extract under "Detaily jednání" or "Detaily" if present
        for candidate in ["detaily jednání", "detaily jednani", "detaily"]:
            extracted = filter_toc_by_section(toc_items, candidate)
            if extracted:
                items_to_render = extracted
                break

    if levels:
        filtered = [it for it in items_to_render if it["level"] in levels]
    else:
        filtered = [it for it in items_to_render if 1 < it["level"] <= max_depth]
        if not filtered:
            filtered = [it for it in items_to_render if it["level"] <= max_depth]

    if not filtered:
        return ""

    # Classic SVJ Page 1 Agenda Card
    if style_family and "svj" in style_family.lower():
        card_title = title_override or catalog.get("svj.agenda_title", "Program shromáždění")
        lines = ['<div class="agenda-toc-container">']
        if card_title:
            lines.append(f'  <div class="toc-title">{html.escape(card_title)}</div>')
        lines.append('  <ol class="agenda-toc-list">')
        for it in filtered:
            raw_title = it["title"]
            # Clean redundant leading numbers so <ol> markers look clean
            clean_title = re.sub(r'^\d+[\.\)]\s*', '', raw_title)
            t = html.escape(clean_title)
            hid = html.escape(it["id"])
            lines.append(f'    <li><a href="#{hid}">{t}</a></li>')
        lines.append('  </ol>')
        lines.append('</div>\n')
        return "\n".join(lines)

    title = title_override or catalog.t("toc.title", default="Table of Contents")
    lines = [f'<nav id="toc" class="table-of-contents" role="doc-toc">']
    if title:
        lines.append(f'  <div class="toc-title">{html.escape(title)}</div>')
    lines.append('  <ul class="toc-list">')
    for it in filtered:
        lvl = it["level"]
        t = html.escape(it["title"])
        hid = html.escape(it["id"])
        lines.append(f'    <li class="toc-item toc-level-{lvl}"><a href="#{hid}">{t}</a></li>')
    lines.append('  </ul>')
    lines.append('</nav>\n')
    return "\n".join(lines)

def inline_toc(
    tokens: List[Token],
    toc_items: List[Dict[str, Any]],
    enabled: bool = True,
    max_depth: int = 3,
    catalog: Optional[I18nCatalog] = None,
    levels: Optional[List[int]] = None,
    style_family: Optional[str] = None
) -> List[Token]:
    """Inlines TOC into tokens matching [[TOC]] or ::: {#toc}, or prepends when enabled."""
    out: List[Token] = []
    placeholder_found = False

    i = 0
    n = len(tokens)
    while i < n:
        tok = tokens[i]

        # Check for paragraph containing [[TOC...]], [TOC...], {{#toc...}}, or {{toc...}}
        if tok.type == "paragraph_open":
            if i + 2 < n and tokens[i+1].type == "inline" and tokens[i+2].type == "paragraph_close":
                text = tokens[i+1].content.strip()
                m_toc = re.match(r"^(?:\[\[TOC\b|\[TOC\b|\{\{#?toc\b)(.*)(?:\]\]|\]|\}\})$", text, re.IGNORECASE)
                if m_toc or text.upper() in {"[[TOC]]", "[TOC]", "{{#TOC}}", "{{TOC}}"}:
                    placeholder_found = True
                    raw_attrs = m_toc.group(1).strip() if m_toc else ""
                    parsed_attrs = parse_toc_attributes("", raw_attrs)
                    rendered = render_toc_html(
                        toc_items,
                        catalog=catalog,
                        max_depth=max_depth,
                        levels=parsed_attrs.get("levels", levels),
                        style_family=style_family,
                        section=parsed_attrs.get("section"),
                        title_override=parsed_attrs.get("title")
                    )
                    if rendered:
                        toc_tok = Token("html_block", "", 0)
                        toc_tok.content = rendered
                        out.append(toc_tok)
                    i += 3
                    continue

        # Check for div container with id="toc"
        if tok.type == "container_pandoc_div_open" or tok.type == "html_block":
            info_str = getattr(tok, "info", "") or ""
            content_str = getattr(tok, "content", "") or ""
            if 'id="toc"' in content_str or 'id="toc"' in info_str or "#toc" in info_str:
                placeholder_found = True
                parsed_attrs = parse_toc_attributes(info_str, content_str)
                # Consume until matching close
                depth = 1
                i += 1
                while i < n and depth > 0:
                    if tokens[i].type.endswith("_open"):
                        depth += 1
                    elif tokens[i].type.endswith("_close"):
                        depth -= 1
                    i += 1

                rendered = render_toc_html(
                    toc_items,
                    catalog=catalog,
                    max_depth=max_depth,
                    levels=parsed_attrs.get("levels", levels),
                    style_family=style_family,
                    section=parsed_attrs.get("section"),
                    title_override=parsed_attrs.get("title")
                )
                if rendered:
                    toc_tok = Token("html_block", "", 0)
                    toc_tok.content = rendered
                    out.append(toc_tok)
                continue

        out.append(tok)
        i += 1

    # If no placeholder was found and document TOC is requested, inject after first H1
    if enabled and not placeholder_found:
        rendered = render_toc_html(
            toc_items,
            catalog=catalog,
            max_depth=max_depth,
            levels=levels,
            style_family=style_family
        )
        if rendered:
            h1_idx = None
            for idx, tok in enumerate(out):
                if tok.type == "heading_close" and tok.tag == "h1":
                    h1_idx = idx + 1
                    break

            toc_tok = Token("html_block", "", 0)
            toc_tok.content = rendered
            if h1_idx is not None:
                out.insert(h1_idx, toc_tok)
            else:
                out.insert(0, toc_tok)

    return out

def toc_plugin(
    md,
    toc_items: Optional[List[Dict[str, Any]]] = None,
    enabled: bool = True,
    max_depth: int = 3,
    catalog: Optional[I18nCatalog] = None
) -> None:
    """Plugin wrapper for table of contents."""
    pass
