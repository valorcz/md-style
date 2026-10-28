"""
core/parser/transforms/callouts.py
Transforms GitHub-style alert blockquotes into styled callout containers.
Supports: [!NOTE], [!TIP], [!IMPORTANT], [!WARNING], [!CAUTION],
          [!CRITICAL], [!INFO], [!SUCCESS], [!DANGER], [!EVIDENCE], [!FINDING].
Zero hardcoded SVGs (uses IconService) and zero hardcoded translations (uses I18nCatalog).
"""

import re
from typing import List, Dict, Any, Optional
from markdown_it.token import Token
from core.icons import IconService
from core.i18n import I18nCatalog

CALLOUT_REGEX = re.compile(
    r"^\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION|CRITICAL|INFO|SUCCESS|DANGER|EVIDENCE|FINDING)\](?:\s+(.*))?$",
    re.IGNORECASE
)

# Semantic mapping to CSS class and external icon name
ALERT_TYPE_MAPPING: Dict[str, Dict[str, str]] = {
    "note":      {"class": "note",      "icon": "info"},
    "info":      {"class": "note",      "icon": "info"},
    "tip":       {"class": "tip",       "icon": "light-bulb"},
    "success":   {"class": "tip",       "icon": "check-circle"},
    "important": {"class": "important", "icon": "report"},
    "warning":   {"class": "warning",   "icon": "alert"},
    "caution":   {"class": "caution",   "icon": "stop"},
    "critical":  {"class": "critical",  "icon": "shield"},
    "danger":    {"class": "critical",  "icon": "shield"},
    "evidence":  {"class": "evidence",  "icon": "search"},
    "finding":   {"class": "finding",   "icon": "checklist"},
}

def transform_callouts(
    tokens: List[Token],
    catalog: Optional[I18nCatalog] = None,
    icon_service: Optional[IconService] = None
) -> List[Token]:
    """Scans token stream and rewrites alert blockquotes to styled callout divs."""
    catalog = catalog or I18nCatalog("en")
    icon_service = icon_service or IconService()

    out: List[Token] = []
    i = 0
    n = len(tokens)

    while i < n:
        tok = tokens[i]
        if tok.type == "blockquote_open":
            if i + 2 < n and tokens[i+1].type == "paragraph_open" and tokens[i+2].type == "inline":
                inline_tok = tokens[i+2]
                content = inline_tok.content.strip()
                first_line = content.split("\n")[0].strip()
                m = CALLOUT_REGEX.match(first_line)
                if m:
                    alert_type = m.group(1).lower()
                    custom_title = m.group(2)
                    mapping = ALERT_TYPE_MAPPING.get(alert_type, ALERT_TYPE_MAPPING["note"])
                    alert_class = mapping["class"]
                    icon_name = mapping["icon"]

                    icon_svg = icon_service.get_svg(icon_name)
                    default_title = catalog.t(f"callouts.{alert_type}", default=alert_type.upper())
                    display_title = custom_title.strip() if custom_title else default_title

                    # Build callout open token
                    c_open = Token("html_block", "", 0)
                    c_open.content = (
                        f'<div class="callout callout-{alert_class}">\n'
                        f'  <div class="callout-header">\n'
                        f'    {icon_svg}\n'
                        f'    <span class="callout-title">{display_title}</span>\n'
                        f'  </div>\n'
                        f'  <div class="callout-content">\n'
                    )
                    out.append(c_open)

                    # Adjust or strip the [!TYPE] marker line from the first paragraph
                    remaining_text = "\n".join(content.split("\n")[1:]).strip()
                    if remaining_text:
                        out.append(tokens[i+1]) # paragraph_open
                        new_inline = Token("inline", "", 0)
                        new_inline.content = remaining_text
                        text_tok = Token("text", "", 0)
                        text_tok.content = remaining_text
                        new_inline.children = [text_tok]
                        out.append(new_inline)
                        out.append(tokens[i+3]) # paragraph_close
                        i += 4
                    else:
                        i += 4

                    # Collect remaining inner tokens until matching blockquote_close
                    depth = 1
                    while i < n and depth > 0:
                        inner = tokens[i]
                        if inner.type == "blockquote_open":
                            depth += 1
                        elif inner.type == "blockquote_close":
                            depth -= 1
                            if depth == 0:
                                c_close = Token("html_block", "", 0)
                                c_close.content = "  </div>\n</div>\n"
                                out.append(c_close)
                                i += 1
                                break
                        out.append(inner)
                        i += 1
                    continue

        out.append(tok)
        i += 1

    return out
