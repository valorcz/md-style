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
    display_title = custom_title.strip() if custom_title else default_title

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
    """Scans token stream and rewrites alert blockquotes to styled callout divs."""
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

                    c_open = Token("html_block", "", 0)
                    c_open.content = build_callout_open(alert_type, custom_title, catalog, icon_service)
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
                                ballot_html = render_ballot_block(catalog) if alert_type == "proposal" else ""
                                c_close.content = f"  </div>\n{ballot_html}</div>\n"
                                out.append(c_close)
                                i += 1
                                break
                        out.append(inner)
                        i += 1
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
