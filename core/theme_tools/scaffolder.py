"""
core/theme_tools/scaffolder.py
Generates starter template boilerplate for new custom themes.
"""

import re
from pathlib import Path
from typing import Optional

from core.config import STYLES_DIR


class ThemeScaffolder:
    """Generates starter template boilerplate for new custom themes."""

    def __init__(self, styles_root: Path = STYLES_DIR):
        self.styles_root = styles_root

    def scaffold(self, target_name: str, extends: str = "base", output_root: Optional[Path] = None) -> Path:
        """Scaffolds a new theme folder with theme.yaml and custom CSS."""
        clean_name = target_name.strip().strip("/").lower()
        if not re.match(r"^[a-z0-9\-_/]+$", clean_name):
            raise ValueError(f"Theme name '{clean_name}' contains invalid characters.")

        root = output_root or self.styles_root
        target_dir = root / clean_name
        target_dir.mkdir(parents=True, exist_ok=True)

        basename = target_dir.name
        css_filename = f"{basename}.css"
        yaml_path = target_dir / "theme.yaml"
        css_path = target_dir / css_filename

        title_words = [w.capitalize() for w in basename.replace("-", " ").replace("_", " ").split()]
        display_title = " ".join(title_words) + " Theme"

        yaml_content = f"""# ==============================================================================
# md-style Theme Definition: {clean_name}
# ==============================================================================
name: {clean_name}
title: "{display_title}"
extends: {extends}

# Cascading stylesheets injected for this theme (relative to this directory)
stylesheets:
  - {css_filename}

# Feature toggles
features:
  interactive_viewer: true
  sticky_tables: true
  break_ranges: true
  callouts: true

# Declarative CSS custom properties
variables:
  --bg-primary: "#ffffff"
  --text-main: "#1e293b"
  --accent: "#3b82f6"
  --page-header-border: "1px solid #cbd5e1"
  --page-footer-border: "1px solid #e2e8f0"

# Paged.js page geometry & print configuration
paged:
  size: A4
  orientation: portrait
  margins:
    top: 22mm
    right: 18mm
    bottom: 22mm
    left: 18mm
  headers:
    left: "{{{{doc_title}}}}"
    center: ""
    right: "string(heading)"
  footers:
    left: "{{{{date}}}}"
    center: ""
    right: "{{{{page_counter}}}}"
  first_page:
    show_header: false
    show_footer: true
"""

        css_content = f"""/* ==============================================================================
 * md-style Theme: {clean_name}
 * ============================================================================== */

/* Page & Typography Defaults */
body {{
  color: var(--text-main, #1e293b);
  background-color: var(--bg-primary, #ffffff);
}}

/* Headings */
h1, h2, h3, h4, h5, h6 {{
  color: var(--text-main, #0f172a);
}}

h1 {{
  border-bottom: 2px solid var(--accent, #3b82f6);
  padding-bottom: 0.3em;
}}

/* Tables */
table {{
  width: 100%;
  border-collapse: collapse;
  margin: 1.5em 0;
}}

th, td {{
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
}}

th {{
  background-color: #f8fafc;
  font-weight: 600;
}}

/* Callouts / Blockquotes */
blockquote {{
  border-left: 4px solid var(--accent, #3b82f6);
  background-color: #f8fafc;
  padding: 0.8em 1.2em;
  margin: 1em 0;
}}
"""

        if not yaml_path.exists():
            yaml_path.write_text(yaml_content, encoding="utf-8")
        if not css_path.exists():
            css_path.write_text(css_content, encoding="utf-8")

        return target_dir
