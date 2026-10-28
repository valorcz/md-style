"""
core/parser/plugins/figures.py
Markdown-it-py plugin that transforms standalone block images (especially vector SVGs)
into semantic <figure> containers with unified, localized <figcaption> numbering.
"""

import html
from typing import Optional, List
from markdown_it import MarkdownIt
from markdown_it.token import Token
from core.diagrams.figures import FigureManager


def figures_plugin(
    md: MarkdownIt,
    figure_manager: Optional[FigureManager] = None,
    lang: str = "en"
):
    """
    Transforms standalone block images into semantic <figure> blocks with localized captions.
    Participates in sequential document-wide figure numbering shared with Mermaid & D2.
    """
    fm = figure_manager or FigureManager(lang=lang)

    def _figure_block_rule(state):
        tokens = state.tokens
        new_tokens: List[Token] = []
        i = 0
        total = len(tokens)

        while i < total:
            # Check if this paragraph is a standalone block image
            if (
                tokens[i].type == "paragraph_open"
                and i + 2 < total
                and tokens[i + 1].type == "inline"
                and tokens[i + 2].type == "paragraph_close"
            ):
                inline_tok = tokens[i + 1]
                children = inline_tok.children or []
                # Ignore purely whitespace or softbreaks around image
                non_trivial = [
                    c for c in children
                    if c.type not in ("softbreak", "text") or (c.content and c.content.strip())
                ]

                if len(non_trivial) == 1 and non_trivial[0].type == "image":
                    img_tok = non_trivial[0]
                    attrs = img_tok.attrs or {}
                    src = attrs.get("src", "")
                    alt = img_tok.content or ""
                    title = attrs.get("title", "")
                    img_id = attrs.get("id", "")
                    custom_class = attrs.get("class", "")

                    is_svg = src.lower().endswith(".svg") or ".svg?" in src.lower()
                    fig_num = fm.next_number()
                    fig_id = img_id or f"fig-{fig_num}"

                    classes = ["figure-container"]
                    if is_svg:
                        classes.append("svg-figure")
                    else:
                        classes.append("image-figure")
                    if custom_class:
                        classes.append(custom_class)

                    # Sizing style from width or style attributes
                    fig_styles = []
                    if "width" in attrs:
                        w_val = str(attrs["width"]).strip()
                        w_css = f"{w_val}px" if w_val.isdigit() else w_val
                        fig_styles.append(f"max-width: {w_css};")
                    if "style" in attrs:
                        fig_styles.append(str(attrs["style"]).strip())
                    fig_style_attr = f' style="{" ".join(fig_styles)}"' if fig_styles else ""

                    # Build caption if title or alt is provided
                    caption_text = title or alt
                    caption_html = ""
                    if caption_text and caption_text.strip():
                        caption_html = fm.format_caption(
                            caption_text.strip(),
                            lang=lang,
                            count=fig_num,
                            caption_class="svg-caption" if is_svg else "figure-caption"
                        )

                    # Remaining attributes for <img> (omitting id/class/title already on figure)
                    extra_attrs = []
                    for k, v in attrs.items():
                        if k not in {"src", "alt", "title", "id", "class"}:
                            extra_attrs.append(f'{html.escape(k)}="{html.escape(str(v))}"')
                    extra_str = (" " + " ".join(extra_attrs)) if extra_attrs else ""

                    wrapper_class = "svg-container" if is_svg else "image-container"
                    img_html = (
                        f'<img src="{html.escape(src)}" alt="{html.escape(alt)}"{extra_str} />'
                    )

                    fig_html = (
                        f'<figure class="{" ".join(classes)}" id="{html.escape(fig_id)}"{fig_style_attr}>\n'
                        f'  <div class="{wrapper_class}">\n'
                        f'    {img_html}\n'
                        f'  </div>{caption_html}\n'
                        f'</figure>\n'
                    )

                    html_tok = Token("html_block", "", 0)
                    html_tok.content = fig_html
                    new_tokens.append(html_tok)
                    i += 3
                    continue

            new_tokens.append(tokens[i])
            i += 1

        state.tokens = new_tokens

    # Register after inline parsing and attributes resolution
    md.core.ruler.push("figures_plugin", _figure_block_rule)
