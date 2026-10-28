"""
core/diagrams/d2.py
Build-time renderer for D2 diagram code blocks.
- Compiles diagrams into vector SVGs via the standalone D2 CLI binary.
- Maps md-style document themes to native D2 themes (Terminal, Neutral, Cool Classics).
- Emits clean fallback containers when D2 CLI is not installed in the environment.
- Formats figure captions with localized labels & numbers.
"""

import re
import html
import shutil
import subprocess
from typing import Dict, Any, Tuple, Optional
from ..diagnostics import logger
from .figures import FigureManager, FIGURE_LABELS

class D2Renderer:
    def __init__(self, figure_manager: Optional[FigureManager] = None):
        self.figure_manager = figure_manager
        self.figure_count = 0
        self._binary: Optional[str] = shutil.which("d2")

    @property
    def is_available(self) -> bool:
        return self._binary is not None

    def format_caption(self, caption_text: str, lang: str = "en", count: int = 1) -> str:
        """Formats figure caption with localized label & number."""
        if not caption_text or not caption_text.strip():
            return ""

        caption_text = caption_text.strip()
        default_label = FIGURE_LABELS.get(lang.lower()[:2], "Figure")

        prefix_pattern = re.compile(r"^([A-Za-z\u00C0-\u017F]+)\s+(\d+)\s*[:\-\u2013\u2014\.]\s*(.*)$")
        m = prefix_pattern.match(caption_text)

        if m:
            prefix_word, num, rest = m.groups()
            lower_prefix = prefix_word.lower()
            if lower_prefix in {"figure", "obrazek", "obrázek", "obrazok", "obrázok", "abbildung", "figura", "rysunek"}:
                return (
                    f'\n  <figcaption class="d2-caption"><span class="figure-label">'
                    f'{html.escape(default_label)} {html.escape(num)}:</span> {html.escape(rest)}</figcaption>'
                )
            else:
                return (
                    f'\n  <figcaption class="d2-caption"><span class="figure-label">'
                    f'{html.escape(prefix_word)} {html.escape(num)}:</span> {html.escape(rest)}</figcaption>'
                )

        return (
            f'\n  <figcaption class="d2-caption"><span class="figure-label">'
            f'{html.escape(default_label)} {count}:</span> {html.escape(caption_text)}</figcaption>'
        )

    def _resolve_d2_theme(self, doc_theme: str) -> str:
        """Maps md-style document theme to a built-in D2 theme ID."""
        low = doc_theme.lower()
        if "cyber" in low or "dark" in low:
            # Theme 301 is 'Terminal', 300 is 'Dark Flagship'
            return "301"
        elif "dossier" in low:
            # Theme 3 is 'Cool Classics'
            return "3"
        elif "svj" in low:
            # Theme 0 is 'Neutral Default'
            return "0"
        elif "school" in low:
            # Theme 4 is 'Mixed Berry Blue'
            return "4"
        return "0"

    def render_figure(
        self,
        code: str,
        id_attr: str = "",
        caption: str = "",
        lang: str = "en",
        theme: str = "base",
        sketch: bool = False,
        line_no: Optional[int] = None
    ) -> Tuple[str, bool]:
        """
        Renders D2 diagram as semantic <figure> container.
        Attempts build-time compilation via D2 CLI; falls back to clean code container if absent.
        Returns: (rendered_html, is_fallback)
        """
        if self.figure_manager:
            self.figure_count = self.figure_manager.next_number()
            caption_html = self.figure_manager.format_caption(
                caption, lang, count=self.figure_count, caption_class="d2-caption"
            )
        else:
            self.figure_count += 1
            caption_html = self.format_caption(caption, lang, self.figure_count)

        id_str = f' id="{html.escape(id_attr)}"' if id_attr else ""
        diagram_ref = f"'{id_attr}'" if id_attr else f"Figure {self.figure_count}"
        line_ref = f" (line {line_no})" if line_no else ""

        d2_theme = self._resolve_d2_theme(theme)

        # 1. Build-time compilation if D2 binary is present
        if self._binary:
            cmd = [self._binary, f"--theme={d2_theme}"]
            if sketch:
                cmd.append("--sketch")
            cmd.extend(["-", "-"])

            try:
                proc = subprocess.run(
                    cmd,
                    input=code.strip(),
                    text=True,
                    capture_output=True,
                    timeout=15
                )

                if proc.returncode == 0 and proc.stdout.strip():
                    svg_content = proc.stdout.strip()
                    return (
                        f'<figure class="d2-diagram" data-engine="d2"{id_str}>\n'
                        f'  <div class="d2-svg-wrapper">\n{svg_content}\n  </div>{caption_html}\n'
                        f'</figure>',
                        False
                    )
                else:
                    err_msg = proc.stderr.strip() or f"Process exited with code {proc.returncode}"
                    logger.error(f"D2 diagram {diagram_ref}{line_ref} execution failed: {err_msg}")
            except Exception as e:
                logger.error(f"D2 diagram {diagram_ref}{line_ref} execution error: {e}")
        else:
            logger.info(
                f"D2 CLI not found; diagram {diagram_ref}{line_ref} rendered as code block. "
                "Install D2 via 'curl -fsSL https://d2lang.com/install.sh | sh' for vector SVG rendering."
            )

        # 2. Fallback container
        escaped_code = html.escape(code.strip())
        fallback_html = (
            f'<figure class="d2-diagram d2-fallback" data-engine="fallback"{id_str}>\n'
            f'  <div class="d2-svg-wrapper">\n'
            f'    <pre class="d2-code"><code>{escaped_code}</code></pre>\n'
            f'  </div>{caption_html}\n'
            f'</figure>'
        )
        return fallback_html, True
