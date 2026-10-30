"""
core/diagrams/geometry.py
Unified SVG Geometry Extraction, Aspect Ratio Classification, and Optical Budgeting.

Single Source of Truth (SSOT) for calculating:
- Intrinsic SVG dimensions (width, height, aspect ratio)
- Orientation classification (portrait, landscape, square, ultrawide)
- Optical sizing & page budgeting (capping tall diagrams to avoid multi-page overflow)
- Standard HTML data attributes and CSS custom properties for uniform styling across
  Mermaid, D2, and plain inline SVGs.
"""

import re
from dataclasses import dataclass, field
from typing import Optional, Tuple, Dict, List


@dataclass
class SVGGeometry:
    """Represents computed intrinsic dimensions and optical layout budget for an SVG."""
    width: float
    height: float
    aspect_ratio: float
    orientation: str  # "portrait", "landscape", "square", "ultrawide"
    budgeted_width: float
    classes: List[str] = field(default_factory=list)
    css_variables: Dict[str, str] = field(default_factory=dict)

    @property
    def class_string(self) -> str:
        """Returns space-separated class names to append to the <figure> element."""
        return (" " + " ".join(self.classes)) if self.classes else ""

    @property
    def style_string(self) -> str:
        """Returns inline CSS style string for custom properties and max-width."""
        if not self.css_variables:
            return ""
        styles = [f"{k}: {v}" for k, v in self.css_variables.items()]
        return f' style="{"; ".join(styles)};"'

    @property
    def data_attributes(self) -> str:
        """Returns standard HTML5 data attributes for client-side viewer inspection."""
        return (
            f' data-orientation="{self.orientation}"'
            f' data-natural-w="{round(self.width, 1)}"'
            f' data-natural-h="{round(self.height, 1)}"'
            f' data-aspect-ratio="{round(self.aspect_ratio, 2)}"'
        )


class SVGGeometryBudgeter:
    """Extracts SVG dimensions and computes optical layout budgets."""

    DEFAULT_MAX_HEIGHT_PX: float = 520.0
    DEFAULT_MAX_PRINT_HEIGHT_MM: float = 135.0
    DEFAULT_PADDING_COMPENSATION_PX: float = 48.0

    @classmethod
    def extract_dimensions(cls, svg_content: str) -> Tuple[Optional[float], Optional[float]]:
        """Extracts width and height in px from SVG viewBox or width/height attributes."""
        if not svg_content:
            return None, None

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

    @classmethod
    def compute(
        cls,
        svg_content: str,
        max_height_px: float = DEFAULT_MAX_HEIGHT_PX,
        padding_px: float = DEFAULT_PADDING_COMPENSATION_PX
    ) -> Optional[SVGGeometry]:
        """Calculates optical geometry, layout budget, and CSS variables for an SVG.
        
        Returns None if dimensions cannot be determined.
        """
        w, h = cls.extract_dimensions(svg_content)
        if not w or not h or w <= 0 or h <= 0:
            return None

        aspect_ratio = w / h

        # Classify orientation
        if aspect_ratio < 0.75:
            orientation = "portrait"
        elif aspect_ratio > 1.8:
            orientation = "ultrawide"
        elif 0.95 <= aspect_ratio <= 1.05:
            orientation = "square"
        else:
            orientation = "landscape"

        # Optical sizing: Never force width to 100% if natural width is smaller.
        # If height would exceed max_height_px, cap width proportionally so that
        # internal diagram typography (~11-13px) stays aligned with body text.
        if h > max_height_px:
            budgeted_w = round(max_height_px * aspect_ratio, 1)
            opt_width = min(w, budgeted_w) + padding_px
        else:
            opt_width = w + padding_px

        classes: List[str] = [f"orientation-{orientation}"]
        if orientation == "portrait":
            classes.append("diagram-tall")
        elif orientation == "ultrawide":
            classes.append("diagram-wide")

        css_vars: Dict[str, str] = {
            "--fig-natural-w": f"{round(w, 1)}px",
            "--fig-natural-h": f"{round(h, 1)}px",
            "--fig-aspect-ratio": str(round(aspect_ratio, 3)),
            "max-width": f"min(100%, {round(opt_width, 1)}px)",
        }

        return SVGGeometry(
            width=w,
            height=h,
            aspect_ratio=aspect_ratio,
            orientation=orientation,
            budgeted_width=opt_width,
            classes=classes,
            css_variables=css_vars
        )
