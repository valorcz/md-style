"""
core/parser/transforms/sections.py
Heading slugification, anchor generation, and Table of Contents (TOC) extraction.
"""

import re
import html
from typing import List, Dict, Any, Tuple
from markdown_it.token import Token

SLUG_CLEAN_RE = re.compile(r"[^\w\s-]", re.UNICODE)
SLUG_SPACE_RE = re.compile(r"[\s_]+", re.UNICODE)

def slugify(text: str) -> str:
    cleaned = SLUG_CLEAN_RE.sub("", text).strip().lower()
    return SLUG_SPACE_RE.sub("-", cleaned) or "section"

def transform_headings_and_extract_toc(tokens: List[Token]) -> Tuple[List[Token], List[Dict[str, Any]]]:
    """Adds id attributes to headings and extracts TOC items."""
    toc: List[Dict[str, Any]] = []
    seen_slugs: Dict[str, int] = {}
    i = 0
    n = len(tokens)

    while i < n:
        tok = tokens[i]
        if tok.type == "heading_open":
            level = int(tok.tag[1]) if len(tok.tag) > 1 and tok.tag[1].isdigit() else 1
            # Next token is inline with heading title
            title_text = ""
            if i + 1 < n and tokens[i+1].type == "inline":
                title_text = tokens[i+1].content.strip()

            base_slug = slugify(title_text)
            if base_slug in seen_slugs:
                seen_slugs[base_slug] += 1
                heading_id = f"{base_slug}-{seen_slugs[base_slug]}"
            else:
                seen_slugs[base_slug] = 0
                heading_id = base_slug

            tok.attrs = tok.attrs or {}
            tok.attrs["id"] = heading_id

            toc.append({
                "level": level,
                "title": title_text,
                "id": heading_id
            })

        i += 1

    return tokens, toc
