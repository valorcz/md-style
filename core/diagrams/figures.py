"""
core/diagrams/figures.py
Unified Figure Manager and Caption Formatter for Mermaid, D2, and SVG/Raster figures.
Ensures document-wide sequential numbering and localized captions.
"""

import re
import html
from typing import Optional, Dict, Tuple

FIGURE_LABELS: Dict[str, str] = {
    "en": "Figure",
    "cs": "Obrázek",
    "cz": "Obrázek",
    "sk": "Obrázok",
    "de": "Abbildung",
    "fr": "Figure",
    "es": "Figura",
    "it": "Figura",
    "pl": "Rysunek",
}


def extract_svg_dimensions(svg_content: str) -> Tuple[Optional[float], Optional[float]]:
    """Extracts width and height in px from SVG viewBox or width/height attributes."""
    # 1. Try viewBox="min_x min_y width height"
    vb_match = re.search(r'viewBox=[\"\x27]([^\"\x27]+)[\"\x27]', svg_content, re.IGNORECASE)
    if vb_match:
        parts = re.split(r'[\s,]+', vb_match.group(1).strip())
        if len(parts) >= 4:
            try:
                w = float(parts[2])
                h = float(parts[3])
                if w > 0 and h > 0:
                    return w, h
            except ValueError:
                pass

    # 2. Try width="..." and height="..." attributes
    w_match = re.search(r'\bwidth=[\"\x27]([0-9.]+)(px)?[\"\x27]', svg_content, re.IGNORECASE)
    h_match = re.search(r'\bheight=[\"\x27]([0-9.]+)(px)?[\"\x27]', svg_content, re.IGNORECASE)
    if w_match and h_match:
        try:
            w = float(w_match.group(1))
            h = float(h_match.group(1))
            if w > 0 and h > 0:
                return w, h
        except ValueError:
            pass

    return None, None


def compute_diagram_layout_attributes(
    svg_content: str,
    max_height_px: float = 520.0,
    max_print_height_mm: float = 135.0
) -> Tuple[str, str]:
    """Computes layout CSS classes and inline styles to optically budget diagram dimensions.
    
    Prevents tall/narrow diagrams from blowing up to 2000px+ heights and consuming
    entire printed pages. Calculates optical width so internal diagram text (~11-13px)
    matches or slightly undershoots body text (~11-14px).
    
    Returns (extra_classes, extra_style_str).
    """
    w, h = extract_svg_dimensions(svg_content)
    if not w or not h or w <= 0 or h <= 0:
        return "", ""

    aspect_ratio = w / h
    extra_classes = []
    style_parts = [
        f"--diagram-natural-w: {round(w, 1)}px",
        f"--diagram-natural-h: {round(h, 1)}px",
    ]

    # Optical sizing: Cap figure max-width so the rendered diagram height never exceeds max_height_px.
    # We add 48px to account for figure horizontal padding across themes (e.g. 24px left/right).
    if h > max_height_px:
        budgeted_w = round(max_height_px * aspect_ratio, 1)
        opt_width = min(w, budgeted_w) + 48.0
    else:
        opt_width = w + 48.0

    style_parts.append(f"max-width: min(100%, {opt_width}px)")

    if aspect_ratio < 0.75:
        extra_classes.append("diagram-tall")
    elif aspect_ratio > 1.8:
        extra_classes.append("diagram-wide")

    cls_str = (" " + " ".join(extra_classes)) if extra_classes else ""
    style_str = f' style="{"; ".join(style_parts)};"'

    return cls_str, style_str


class FigureManager:
    """Tracks sequential figure numbering and formats localized captions across diagram and image engines."""

    def __init__(self, lang: str = "en"):
        self.count: int = 0
        self.lang: str = lang

    def next_number(self) -> int:
        self.count += 1
        return self.count

    def format_caption(
        self,
        caption_text: str,
        lang: Optional[str] = None,
        count: Optional[int] = None,
        caption_class: str = "figure-caption"
    ) -> str:
        """Formats figure caption with localized label & sequential number."""
        if not caption_text or not caption_text.strip():
            return ""

        caption_text = caption_text.strip()
        effective_lang = (lang or self.lang or "en").lower()[:2]
        default_label = FIGURE_LABELS.get(effective_lang, "Figure")
        fig_num = count if count is not None else self.next_number()

        # Match existing patterns like "Figure 1: Title", "Obrázek 1: Title", etc.
        prefix_pattern = re.compile(r"^([A-Za-z\u00C0-\u017F]+)\s+(\d+)\s*[:\-\u2013\u2014\.]\s*(.*)$")
        m = prefix_pattern.match(caption_text)

        if m:
            prefix_word, num_str, rest = m.groups()
            lower_prefix = prefix_word.lower()
            known_prefixes = {
                "figure", "obrazek", "obrázek", "obrazok", "obrázok",
                "abbildung", "figura", "rysunek"
            }
            if lower_prefix in known_prefixes:
                label_to_use = default_label
            else:
                label_to_use = prefix_word

            return (
                f'\n  <figcaption class="{html.escape(caption_class)}">'
                f'<span class="figure-label">{html.escape(label_to_use)} {html.escape(num_str)}:</span> '
                f'{html.escape(rest)}</figcaption>'
            )

        return (
            f'\n  <figcaption class="{html.escape(caption_class)}">'
            f'<span class="figure-label">{html.escape(default_label)} {fig_num}:</span> '
            f'{html.escape(caption_text)}</figcaption>'
        )
