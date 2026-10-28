"""
core/parser/transforms/kpi.py
Transforms Executive Summary and KPI Grid bullet lists into structured
2-column KPI Cards with .kpi-card, .kpi-label, and .kpi-value.
Consistent with original md-style (forensic.lua).
"""

import re
import html
from typing import List, Optional
from markdown_it.token import Token
from markdown_it import MarkdownIt

EXEC_SUMMARY_KEYWORDS = [
    "executive summary", "manažerské shrnutí", "manazerske shrnuti",
    "kpi grid", "kpi dashboard", "přehled metrik", "prehled metrik"
]

def is_exec_summary_heading(text: str) -> bool:
    clean = text.lower().strip()
    return any(kw in clean for kw in EXEC_SUMMARY_KEYWORDS)

def parse_kpi_inline(inline_token: Token, md: Optional[MarkdownIt] = None) -> Optional[tuple[str, str]]:
    """
    Parses an inline token for a **Label:** Value pattern.
    Returns (label_html, value_html) or None.
    """
    children = inline_token.children or []
    if not children:
        # Fallback to regex on content
        content = inline_token.content.strip()
        m = re.match(r"^\*\*(.+?)\*\*[:\s]*(.*)$", content)
        if m:
            label = re.sub(r":\s*$", "", m.group(1).strip())
            val = m.group(2).strip()
            val_html = md.renderInline(val) if md else html.escape(val)
            return label, val_html
        return None

    # Check children for strong_open ... strong_close
    first_idx = 0
    while first_idx < len(children) and children[first_idx].type == "text" and not children[first_idx].content.strip():
        first_idx += 1

    if first_idx >= len(children) or children[first_idx].type != "strong_open":
        return None

    # Extract label inside strong
    label_parts = []
    strong_close_idx = -1
    for idx in range(first_idx + 1, len(children)):
        c = children[idx]
        if c.type == "strong_close":
            strong_close_idx = idx
            break
        label_parts.append(c.content)

    if strong_close_idx == -1:
        return None

    raw_label = "".join(label_parts).strip()
    clean_label = re.sub(r":\s*$", "", raw_label).strip()

    # Remaining children are value
    val_children = []
    start_val = strong_close_idx + 1

    # Skip leading colon/space in text
    if start_val < len(children) and children[start_val].type == "text":
        txt = children[start_val].content
        txt_stripped = re.sub(r"^\s*:\s*", "", txt)
        if txt_stripped:
            # Clone token with stripped text
            new_tok = Token(children[start_val].type, children[start_val].tag, children[start_val].nesting)
            new_tok.attrs = dict(children[start_val].attrs or {})
            new_tok.content = txt_stripped
            val_children.append(new_tok)
        start_val += 1

    for idx in range(start_val, len(children)):
        val_children.append(children[idx])

    if md and val_children:
        val_html = md.renderer.renderInline(val_children, md.options, {})
    else:
        val_html = "".join(c.content for c in val_children).strip()

    return clean_label, val_html

def transform_kpi_grids(tokens: List[Token], md: Optional[MarkdownIt] = None) -> List[Token]:
    """
    Transforms bullet lists inside ::: {.kpi-grid} or under Executive Summary headings
    into semantic .kpi-card elements.
    """
    out: List[Token] = []
    i = 0
    n = len(tokens)
    preceding_heading = ""

    while i < n:
        tok = tokens[i]

        # Track preceding headings
        if tok.type == "heading_open":
            if i + 1 < n and tokens[i+1].type == "inline":
                preceding_heading = tokens[i+1].content.strip()
            out.append(tok)
            i += 1
            continue

        # Case 1: Explicit ::: {.kpi-grid} container
        if tok.type == "container_pandoc_div_open" and "kpi-grid" in (tok.info or ""):
            out.append(tok)
            i += 1
            # Check if next token is a bullet_list_open
            if i < n and tokens[i].type == "bullet_list_open":
                cards_html = []
                list_depth = 0
                while i < n:
                    ltok = tokens[i]
                    if ltok.type == "bullet_list_open":
                        list_depth += 1
                    elif ltok.type == "bullet_list_close":
                        list_depth -= 1
                        if list_depth == 0:
                            i += 1
                            break
                    elif ltok.type == "inline" and list_depth == 1:
                        parsed = parse_kpi_inline(ltok, md)
                        if parsed:
                            lbl, val = parsed
                            cards_html.append(
                                f'  <div class="kpi-card">\n'
                                f'    <div class="kpi-label">{html.escape(lbl)}</div>\n'
                                f'    <div class="kpi-value">{val}</div>\n'
                                f'  </div>'
                            )
                        else:
                            val_html = md.renderer.renderInline(ltok.children or [ltok], md.options, {}) if md else html.escape(ltok.content)
                            cards_html.append(
                                f'  <div class="kpi-card kpi-card-full">\n'
                                f'    <div class="kpi-value">{val_html}</div>\n'
                                f'  </div>'
                            )
                    i += 1

                if cards_html:
                    card_block = Token("html_block", "", 0)
                    card_block.content = "\n" + "\n".join(cards_html) + "\n"
                    out.append(card_block)
            continue

        # Case 2: Implicit Executive Summary bullet list directly following heading
        if is_exec_summary_heading(preceding_heading) and tok.type == "bullet_list_open":
            cards_html = []
            list_depth = 0
            list_start_idx = i
            has_kpi_items = False

            temp_i = i
            while temp_i < n:
                ltok = tokens[temp_i]
                if ltok.type == "bullet_list_open":
                    list_depth += 1
                elif ltok.type == "bullet_list_close":
                    list_depth -= 1
                    if list_depth == 0:
                        temp_i += 1
                        break
                elif ltok.type == "inline" and list_depth == 1:
                    parsed = parse_kpi_inline(ltok, md)
                    if parsed:
                        has_kpi_items = True
                        lbl, val = parsed
                        cards_html.append(
                            f'  <div class="kpi-card">\n'
                            f'    <div class="kpi-label">{html.escape(lbl)}</div>\n'
                            f'    <div class="kpi-value">{val}</div>\n'
                            f'  </div>'
                        )
                temp_i += 1

            if has_kpi_items and cards_html:
                wrapper_open = Token("html_block", "", 0)
                wrapper_open.content = '<div class="kpi-grid">\n'
                out.append(wrapper_open)

                card_block = Token("html_block", "", 0)
                card_block.content = "\n".join(cards_html) + "\n"
                out.append(card_block)

                wrapper_close = Token("html_block", "", 0)
                wrapper_close.content = '</div>\n'
                out.append(wrapper_close)

                i = temp_i
                preceding_heading = ""
                continue

        out.append(tok)
        i += 1

    return out
