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

# Delegate to SVGGeometryBudgeter for dimension extraction and budgeting
from .geometry import SVGGeometryBudgeter, SVGGeometry


def extract_svg_dimensions(svg_content: str) -> Tuple[Optional[float], Optional[float]]:
    """Backward-compatible helper delegating to SVGGeometryBudgeter."""
    return SVGGeometryBudgeter.extract_dimensions(svg_content)


def compute_diagram_layout_attributes(
    svg_content: str,
    max_height_px: float = 520.0,
    max_print_height_mm: float = 135.0
) -> Tuple[str, str]:
    """Backward-compatible helper returning (class_string, style_string)."""
    geom = SVGGeometryBudgeter.compute(svg_content, max_height_px=max_height_px)
    if not geom:
        return "", ""
    return geom.class_string, geom.style_string


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
