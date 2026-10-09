"""
core/parser/transforms/tables.py
Transforms tables: wraps in .table-wrapper, identifies timestamp ranges with <wbr> breaks,
and flags numeric columns with .num alignment.
"""

import re
from typing import List, Optional
from markdown_it.token import Token

# Timestamp range pattern: "2026-09-29 10:00:00 - 2026-09-29 12:00:00" or similar
TIMESTAMP_RANGE_RE = re.compile(
    r"(\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?)\s*([–—\-]|\.\.)\s*(\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2})?)?)",
    re.IGNORECASE
)

NUMERIC_RE = re.compile(r"^\s*[-+]?(?:\d{1,3}(?:[ ,]\d{3})*|\d+)(?:\.\d+)?%?\s*$")

# Timestamp pattern: single datetime or date
TIMESTAMP_RE = re.compile(
    r"^\s*(\d{4}-\d{2}-\d{2}(?:[ T]\d{2}:\d{2}(?::\d{2})?(?:Z|[+-]\d{2}:?\d{2}| UTC)?)?|\d{2}:\d{2}(?::\d{2})?(?: UTC)?)\s*$",
    re.IGNORECASE
)

# Cryptographic hash pattern (MD5=32, SHA-1=40, SHA-256=64 hex chars)
HEX_HASH_RE = re.compile(r"\b([a-fA-F0-9]{32,64})\b")

def format_time_ranges(text: str) -> str:
    """Wraps datetime ranges in <span class='time-range timestamp nowrap'> with break opportunities (<wbr>)."""
    def _repl(m):
        t1, sep, t2 = m.group(1), m.group(2), m.group(3)
        return f'<span class="time-range timestamp nowrap">{t1}<wbr> {sep} <wbr>{t2}</span>'
    return TIMESTAMP_RANGE_RE.sub(_repl, text)

def is_numeric_text(text: str) -> bool:
    return bool(NUMERIC_RE.match(text.strip()))

def is_timestamp_text(text: str) -> bool:
    return bool(TIMESTAMP_RE.match(text.strip()))

def is_hash_text(text: str) -> bool:
    clean = text.strip()
    return bool(len(clean) in (32, 40, 64) and HEX_HASH_RE.fullmatch(clean))

def transform_tables(tokens: List[Token]) -> List[Token]:
    """Wraps tables in .table-wrapper and injects classes for timestamps and cryptographic hashes."""
    out: List[Token] = []
    i = 0
    n = len(tokens)
    in_table_cell = False
    current_td_idx = None

    while i < n:
        tok = tokens[i]
        if tok.type == "table_open":
            wrapper_open = Token("html_block", "", 0)
            wrapper_open.content = '<div class="table-wrapper">\n'
            out.append(wrapper_open)
            out.append(tok)
            i += 1
            continue

        if tok.type == "table_close":
            out.append(tok)
            wrapper_close = Token("html_block", "", 0)
            wrapper_close.content = '</div>\n'
            out.append(wrapper_close)
            i += 1
            continue

        if tok.type == "td_open":
            in_table_cell = True
            current_td_idx = len(out)
            out.append(tok)
            i += 1
            continue

        if tok.type == "td_close":
            in_table_cell = False
            current_td_idx = None
            out.append(tok)
            i += 1
            continue

        # In table cells, check inline content for timestamps and hashes
        if tok.type == "inline" and in_table_cell and current_td_idx is not None:
            content = tok.content.strip()
            td_tok = out[current_td_idx]
            td_tok.attrs = td_tok.attrs or {}
            existing_class = td_tok.attrs.get("class", "")

            # 1. Timestamp Range
            if TIMESTAMP_RANGE_RE.search(tok.content):
                new_html = format_time_ranges(tok.content)
                html_tok = Token("html_inline", "", 0)
                html_tok.content = new_html
                tok.children = [html_tok]
                tok.content = new_html
                td_tok.attrs["class"] = f"{existing_class} timestamp nowrap".strip()

            # 2. Single Timestamp
            elif is_timestamp_text(content):
                td_tok.attrs["class"] = f"{existing_class} timestamp nowrap".strip()

            # 3. Cryptographic Hash
            elif is_hash_text(content):
                td_tok.attrs["class"] = f"{existing_class} hash break-all".strip()

            # Check individual code tokens inside children for hashes
            if tok.children:
                for child in tok.children:
                    if child.type == "code_inline" and is_hash_text(child.content):
                        child.attrs = child.attrs or {}
                        c_cls = child.attrs.get("class", "")
                        child.attrs["class"] = f"{c_cls} hash break-all".strip()
                        td_tok.attrs["class"] = f"{td_tok.attrs.get('class', '')} hash break-all".strip()

        out.append(tok)
        i += 1

    return out
