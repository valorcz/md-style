"""
core/diagrams/mermaid.py
Pre-renders Mermaid diagrams to SVG using beautiful-mermaid bundle via Bun or Node.js.
Provides client fallback when beautiful-mermaid encountered unsupported diagram syntax.
"""

import os
import re
import json
import html
import shutil
import subprocess
from typing import Dict, Any, Tuple, Optional, List
from pathlib import Path
from ..config import MERMAID_BUNDLE
from ..diagnostics import logger

FIGURE_LABELS = {
    "en": "Figure",
    "cs": "Obrázek",
    "cz": "Obrázek",
    "sk": "Obrázok",
    "de": "Abbildung",
    "fr": "Figure",
    "es": "Figura",
    "it": "Figura",
    "pl": "Rysunek"
}

class MermaidRenderer:
    def __init__(self, bundle_path: Optional[Path] = None):
        self.bundle_path = bundle_path or MERMAID_BUNDLE
        self.runtime = self._detect_runtime()
        self.figure_count = 0
        self.has_fallback = False

    def _detect_runtime(self) -> Optional[str]:
        """Detects whether bun or node is available."""
        if shutil.which("bun"):
            return "bun"
        if shutil.which("node"):
            return "node"
        return None

    def format_caption(self, caption_text: str, lang: str = "en", count: int = 1) -> str:
        """Formats figure caption with localized label & number."""
        if not caption_text or not caption_text.strip():
            return ""

        caption_text = caption_text.strip()
        default_label = FIGURE_LABELS.get(lang.lower()[:2], "Figure")

        # Match patterns like "Figure 1: Title", "Figure 1 - Title", "Obrázek 1: Title"
        prefix_pattern = re.compile(r"^([A-Za-z\u00C0-\u017F]+)\s+(\d+)\s*[:\-\u2013\u2014\.]\s*(.*)$")
        m = prefix_pattern.match(caption_text)

        if m:
            prefix_word, num, rest = m.groups()
            lower_prefix = prefix_word.lower()
            if lower_prefix in {"figure", "obrazek", "obrázek", "obrazok", "obrázok", "abbildung", "figura", "rysunek"}:
                return (
                    f'\n  <figcaption class="mermaid-caption"><span class="figure-label">'
                    f'{html.escape(default_label)} {html.escape(num)}:</span> {html.escape(rest)}</figcaption>'
                )
            else:
                return (
                    f'\n  <figcaption class="mermaid-caption"><span class="figure-label">'
                    f'{html.escape(prefix_word)} {html.escape(num)}:</span> {html.escape(rest)}</figcaption>'
                )

        return (
            f'\n  <figcaption class="mermaid-caption"><span class="figure-label">'
            f'{html.escape(default_label)} {count}:</span> {html.escape(caption_text)}</figcaption>'
        )

    def render_diagram(self, code: str) -> Dict[str, Any]:
        """Executes beautiful-mermaid bundle on the given diagram code."""
        if not self.runtime or not self.bundle_path.exists():
            return {"success": False, "reason": "no_runtime", "error": "No JS runtime or bundle missing"}

        cmd = [self.runtime, str(self.bundle_path), "--theme=zinc-light", "--transparent"]
        try:
            res = subprocess.run(
                cmd,
                input=code,
                capture_output=True,
                text=True,
                timeout=12,
                check=False
            )
            stdout = res.stdout.strip()
            if stdout:
                data = json.loads(stdout)
                return data
            return {"success": False, "reason": "empty_output", "error": res.stderr}
        except subprocess.TimeoutExpired:
            return {"success": False, "reason": "timeout", "error": "Render timed out after 12s"}
        except Exception as e:
            return {"success": False, "reason": "exception", "error": str(e)}

    def render_figure(self, code: str, id_attr: str = "", caption: str = "", lang: str = "en") -> str:
        """Renders diagram and formats as <figure> element."""
        self.figure_count += 1
        caption_html = self.format_caption(caption, lang, self.figure_count)
        id_str = f' id="{html.escape(id_attr)}"' if id_attr else ""

        res = self.render_diagram(code)
        if res.get("success") and res.get("svg"):
            return (
                f'<figure class="mermaid-diagram" data-engine="beautiful-mermaid"{id_str}>\n'
                f'  <div class="mermaid-svg-wrapper">\n{res["svg"]}\n  </div>{caption_html}\n'
                f'</figure>'
            )
        else:
            self.has_fallback = True
            reason = res.get("reason", "error")
            err = res.get("error", "")
            logger.debug(f"Mermaid fallback ({reason}): {err}")
            return (
                f'<figure class="mermaid-diagram mermaid-fallback" data-engine="client"{id_str}>\n'
                f'  <div class="mermaid-svg-wrapper">\n    <pre class="mermaid">\n{html.escape(code.strip())}\n    </pre>\n  </div>{caption_html}\n'
                f'</figure>'
            )

    def transform_markdown(self, content: str, lang: str = "en") -> Tuple[str, int, int]:
        """
        Scans markdown for Mermaid codeblocks and transforms them to HTML figures.
        Returns: (transformed_markdown, rendered_count, fallback_count)
        """
        # Match ``` {.mermaid ...} or ```mermaid ...
        # e.g.: ``` {.mermaid #fig-attack-chain caption="Figure 1: Title"}
        pattern = re.compile(
            r"```\s*(?:\{\s*\.mermaid\s*([^}]*)\}|mermaid\b([^\n]*))\n(.*?)```",
            re.DOTALL
        )

        rendered_count = 0
        fallback_count = 0

        def replace_block(match: re.Match) -> str:
            nonlocal rendered_count, fallback_count
            attr_part1 = match.group(1) or ""
            attr_part2 = match.group(2) or ""
            attrs_str = (attr_part1 + " " + attr_part2).strip()
            code = match.group(3).strip()

            id_attr = ""
            caption = ""

            # Extract #id
            id_m = re.search(r"#([A-Za-z0-9_\-]+)", attrs_str)
            if id_m:
                id_attr = id_m.group(1)

            # Extract caption="..." or title="..."
            cap_m = re.search(r'(?:caption|title)=["\']([^"\']+)["\']', attrs_str)
            if cap_m:
                caption = cap_m.group(1)

            initial_fallback = self.has_fallback
            self.has_fallback = False

            html_fig = self.render_figure(code, id_attr=id_attr, caption=caption, lang=lang)

            if self.has_fallback:
                fallback_count += 1
            else:
                rendered_count += 1

            # Restore overall fallback flag
            self.has_fallback = initial_fallback or self.has_fallback

            # Wrap in HTML raw block markers or return directly as HTML block
            return f"\n\n{html_fig}\n\n"

        transformed = pattern.sub(replace_block, content)
        return transformed, rendered_count, fallback_count
