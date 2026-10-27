"""
core/parser/plugins/callouts.py
Native markdown-it-py plugin for GitHub-style Alerts and Admonition Callout Boxes.
Supports:
  1. GitHub-style alerts:
     > [!NOTE] Custom Header
     > Content here...
  2. Container-style callouts:
     ::: note Custom Header
     Content here...
     :::
Supports all standard and domain-specific types:
  note, tip, important, warning, caution, critical, danger, evidence, finding, info, success, proposal.
Integrates IconService vector SVGs, I18nCatalog localization, and automated voting ballots for proposals.
"""

import re
import html
from typing import List, Dict, Any, Optional
from markdown_it import MarkdownIt
from markdown_it.token import Token
from mdit_py_plugins.container import container_plugin
from core.icons import IconService
from core.i18n import I18nCatalog

CALLOUT_REGEX = re.compile(
    r"^\s*\[!(NOTE|TIP|IMPORTANT|WARNING|CAUTION|CRITICAL|INFO|SUCCESS|DANGER|EVIDENCE|FINDING|PROPOSAL)\](?:\s+(.*))?$",
    re.IGNORECASE
)

ALERT_TYPE_MAPPING: Dict[str, Dict[str, str]] = {
    "note":      {"class": "note",             "icon": "info"},
    "info":      {"class": "note",             "icon": "info"},
    "tip":       {"class": "tip",              "icon": "light-bulb"},
    "success":   {"class": "tip",              "icon": "check-circle"},
    "important": {"class": "important",        "icon": "report"},
    "warning":   {"class": "warning",          "icon": "alert"},
    "caution":   {"class": "caution",          "icon": "stop"},
    "critical":  {"class": "critical",         "icon": "shield"},
    "danger":    {"class": "critical",         "icon": "shield"},
    "evidence":  {"class": "evidence",         "icon": "search"},
    "finding":   {"class": "finding",          "icon": "checklist"},
    "proposal":  {"class": "proposal-callout", "icon": "checklist"},
}

def render_ballot_block(catalog: I18nCatalog) -> str:
    """Renders localized ballot options for proposal callouts."""
    prompt = catalog.t("ballots.prompt", default="HLASOVÁNÍ:")
    pro = catalog.t("ballots.pro", default="PRO")
    against = catalog.t("ballots.against", default="PROTI")
    abstain = catalog.t("ballots.abstain", default="ZDRŽEL SE")

    return (
        f'  <div class="proposal-ballot">\n'
        f'    <span class="ballot-prompt">{html.escape(prompt)}</span>\n'
        f'    <span class="ballot-option ballot-pro"><span class="ballot-box-icon">☐</span> {html.escape(pro)}</span>\n'
        f'    <span class="ballot-option ballot-con"><span class="ballot-box-icon">☐</span> {html.escape(against)}</span>\n'
        f'    <span class="ballot-option ballot-abs"><span class="ballot-box-icon">☐</span> {html.escape(abstain)}</span>\n'
        f'  </div>\n'
    )

def build_callout_open(alert_type: str, custom_title: Optional[str], catalog: I18nCatalog, icon_service: IconService) -> str:
    mapping = ALERT_TYPE_MAPPING.get(alert_type, ALERT_TYPE_MAPPING["note"])
    alert_class = mapping["class"]
    icon_name = mapping["icon"]

    icon_svg = icon_service.get_svg(icon_name)
    default_title = catalog.t(f"callouts.{alert_type}", default=alert_type.upper())
    if custom_title:
        # Strip potential markdown formatting (bold, italic, code) or trailing colon
        clean_title = re.sub(r"^[`*_]{1,3}(.*?)[`*_]{1,3}:?$", r"\1", custom_title.strip()).rstrip(":").strip()
        display_title = clean_title if clean_title else default_title
    else:
        display_title = default_title

    css_classes = f"callout callout-{alert_class} {alert_class}"
    return (
        f'<div class="{css_classes}">\n'
        f'  <div class="callout-header">\n'
        f'    {icon_svg}\n'
        f'    <span class="callout-title">{html.escape(display_title)}</span>\n'
        f'  </div>\n'
        f'  <div class="callout-content">\n'
    )

def transform_blockquote_callouts(tokens: List[Token], catalog: I18nCatalog, icon_service: IconService) -> List[Token]:
    """Scans token stream and rewrites alert blockquotes to styled callout divs, preserving all inline markdown."""
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
                children = list(inline_tok.children or [])

                m = CALLOUT_REGEX.match(first_line)
                m_leg = None
                alert_type = None
                custom_title = None

                if m:
                    alert_type = m.group(1).lower()
                    custom_title = m.group(2)
                elif len(children) >= 4 and children[1].type == "strong_open":
                    # Only convert single-keyword legacy callouts: > **NOTE**: or > **WARNING**:
                    # Multi-word lead tags (e.g. > **CRITICAL FINDING**:) remain clean signature blockquotes
                    tag_candidate = children[2].content.strip().lower()
                    if tag_candidate in {"note", "warning", "tip", "caution", "important", "critical", "danger"} and len(children) > 4:
                        colon_check = children[4].content if len(children) > 4 else ""
                        if re.match(r"^\s*:\s*", colon_check):
                            alert_type = tag_candidate
                            m_leg = True
                            custom_title = None

                if alert_type:
                    c_open = Token("html_block", "", 0)
                    c_open.content = build_callout_open(alert_type, custom_title, catalog, icon_service)
                    out.append(c_open)

                    # Adjust children and content while preserving all rich inline tokens
                    if m_leg:
                        # Strip bold marker and colon
                        colon_tok = children[4]
                        colon_tok.content = re.sub(r"^\s*:\s*", "", colon_tok.content)
                        inline_tok.children = children[4:]
                        inline_tok.content = re.sub(r"^\s*(?:\*\*|__)[^*_]+(?:\*\*|__)\s*:\s*", "", inline_tok.content)
                        out.append(tokens[i+1]) # paragraph_open
                        out.append(inline_tok)
                        out.append(tokens[i+3]) # paragraph_close
                        i += 4
                    elif m:
                        # Find first break (softbreak or hardbreak) in children
                        break_idx = None
                        for idx, ch in enumerate(children):
                            if ch.type in ("softbreak", "hardbreak"):
                                break_idx = idx
                                break

                        if break_idx is not None:
                            # Alert header on line 1, remaining lines in paragraph are body text
                            remaining_children = children[break_idx + 1:]
                            remaining_content = "\n".join(content.split("\n")[1:]).strip()
                            if remaining_children:
                                out.append(tokens[i+1]) # paragraph_open
                                inline_tok.children = remaining_children
                                inline_tok.content = remaining_content
                                out.append(inline_tok)
                                out.append(tokens[i+3]) # paragraph_close
                            i += 4
                        else:
                            # Single line alert: > [!NOTE] Custom Title
                            if children:
                                children[0].content = re.sub(r"^\s*\[![A-Za-z]+\]\s*", "", children[0].content)
                                inline_tok.content = re.sub(r"^\s*\[![A-Za-z]+\]\s*", "", inline_tok.content)
                                if custom_title and custom_title.strip():
                                    title_escaped = re.escape(custom_title.strip())
                                    inline_tok.content = re.sub(rf"^\s*{title_escaped}\s*", "", inline_tok.content).strip()
                                    children[0].content = re.sub(rf"^\s*{title_escaped}\s*", "", children[0].content).strip()
                                    children = [c for c in children if c.content or c.type != "text"]

                                if inline_tok.content:
                                    out.append(tokens[i+1]) # paragraph_open
                                    inline_tok.children = children
                                    out.append(inline_tok)
                                    out.append(tokens[i+3]) # paragraph_close
                            i += 4

                    # Collect remaining inner tokens until matching blockquote_close
                    inner_tokens: List[Token] = []
                    depth = 1
                    while i < n and depth > 0:
                        inner = tokens[i]
                        if inner.type == "blockquote_open":
                            depth += 1
                            inner_tokens.append(inner)
                        elif inner.type == "blockquote_close":
                            depth -= 1
                            if depth == 0:
                                i += 1
                                break
                            inner_tokens.append(inner)
                        else:
                            inner_tokens.append(inner)
                        i += 1

                    if inner_tokens:
                        transformed_inner = transform_blockquote_callouts(inner_tokens, catalog, icon_service)
                        out.extend(transformed_inner)

                    c_close = Token("html_block", "", 0)
                    ballot_html = render_ballot_block(catalog) if alert_type == "proposal" else ""
                    c_close.content = f"  </div>\n{ballot_html}</div>\n"
                    out.append(c_close)
                    continue

        out.append(tok)
        i += 1

    return out

def callouts_plugin(
    md: MarkdownIt,
    catalog: Optional[I18nCatalog] = None,
    icon_service: Optional[IconService] = None
) -> None:
    """Registers unified callouts plugin for blockquotes and container fences."""
    catalog = catalog or I18nCatalog("en")
    icon_service = icon_service or IconService()

    # 1. Register Core rule for blockquote alerts (> [!NOTE])
    def callouts_core_rule(state) -> None:
        state.tokens = transform_blockquote_callouts(state.tokens, catalog, icon_service)

    md.core.ruler.push("callouts", callouts_core_rule)

    # 2. Register Container rules for fenced callouts (::: note Title)
    for alert_name in ALERT_TYPE_MAPPING.keys():
        def make_validate(cur_name: str):
            return lambda params, *args: params.strip().split()[0].lower() == cur_name

        def make_render(cur_name: str):
            def render_fn(self, tokens, idx, _options, env):
                tok = tokens[idx]
                if tok.nesting == 1:
                    parts = tok.info.strip().split(None, 1)
                    custom_title = parts[1] if len(parts) > 1 else None
                    return build_callout_open(cur_name, custom_title, catalog, icon_service)
                else:
                    ballot_html = render_ballot_block(catalog) if cur_name == "proposal" else ""
                    return f"  </div>\n{ballot_html}</div>\n"
            return render_fn

        md.use(
            container_plugin,
            name=f"callout_{alert_name}",
            validate=make_validate(alert_name),
            render=make_render(alert_name)
        )
