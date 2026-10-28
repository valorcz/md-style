"""
core/diagrams/mermaid.py
Dual-mode renderer for Mermaid diagram code blocks.
- Build-time: Compiles diagrams into beautiful vector SVGs via beautiful-mermaid in viewer/scripts/render-diagram.mjs.
- Client-time: Emits clean fallback containers for viewer.bundle.js when JS runtimes are absent or schemas are unsupported.
- Full CLI diagnostics on stderr for invalid diagram syntax.
"""

import re
import html
import shutil
import subprocess
import json
from typing import Dict, Any, Tuple, Optional
from ..diagnostics import logger
from ..config import VIEWER_DIR, MERMAID_SCRIPT
from .figures import FigureManager, FIGURE_LABELS

class MermaidRenderer:
    def __init__(self, figure_manager: Optional[FigureManager] = None):
        self.figure_manager = figure_manager
        self.figure_count = 0
        self._runtime: Optional[str] = None
        self._detect_runtime()

    def _detect_runtime(self) -> Optional[str]:
        """Detects Node.js or Bun runtime."""
        if shutil.which("bun"):
            self._runtime = "bun"
        elif shutil.which("node"):
            self._runtime = "node"
        else:
            self._runtime = None
        return self._runtime

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

    def render_figure(
        self,
        code: str,
        id_attr: str = "",
        caption: str = "",
        lang: str = "en",
        theme: str = "zinc-light",
        line_no: Optional[int] = None
    ) -> Tuple[str, bool]:
        """
        Renders diagram as semantic <figure> container.
        Attempts build-time compilation via beautiful-mermaid; falls back to client container.
        Returns: (rendered_html, is_fallback)
        """
        if self.figure_manager:
            self.figure_count = self.figure_manager.next_number()
            caption_html = self.figure_manager.format_caption(
                caption, lang, count=self.figure_count, caption_class="mermaid-caption"
            )
        else:
            self.figure_count += 1
            caption_html = self.format_caption(caption, lang, self.figure_count)

        id_str = f' id="{html.escape(id_attr)}"' if id_attr else ""
        diagram_ref = f"'{id_attr}'" if id_attr else f"Figure {self.figure_count}"
        line_ref = f" (line {line_no})" if line_no else ""

        # Map document theme to beautiful-mermaid theme
        bm_theme = "zinc-dark" if ("dark" in theme.lower() or "cyber" in theme.lower()) else "zinc-light"

        # Check if build-time beautiful-mermaid execution is possible
        if self._runtime and MERMAID_SCRIPT.exists():
            try:
                proc = subprocess.run(
                    [self._runtime, str(MERMAID_SCRIPT), f"--theme={bm_theme}", "--transparent"],
                    input=code.strip(),
                    text=True,
                    capture_output=True,
                    timeout=15,
                    cwd=str(VIEWER_DIR)
                )

                if proc.returncode == 0 and proc.stdout.strip():
                    res = json.loads(proc.stdout.strip())
                    if res.get("success") and res.get("svg"):
                        svg_content = res["svg"].strip()
                        engine = res.get("engine", "beautiful-mermaid")
                        return (
                            f'<figure class="mermaid-diagram" data-engine="{engine}"{id_str}>\n'
                            f'  <div class="mermaid-svg-wrapper">\n{svg_content}\n  </div>{caption_html}\n'
                            f'</figure>',
                            False
                        )
                    elif res.get("reason") == "unsupported_schema":
                        logger.warning(
                            f"Mermaid diagram {diagram_ref}{line_ref} schema not supported by beautiful-mermaid. Emitting client-side fallback."
                        )
                    else:
                        err_msg = res.get("error") or "Unknown render error"
                        logger.error(
                            f"Mermaid diagram {diagram_ref}{line_ref} render error: {err_msg}"
                        )
                else:
                    err_msg = proc.stderr.strip() or f"Process exited with code {proc.returncode}"
                    logger.error(f"Mermaid diagram {diagram_ref}{line_ref} execution failed: {err_msg}")
            except Exception as e:
                logger.error(f"Mermaid diagram {diagram_ref}{line_ref} execution error: {e}")
        elif not self._runtime:
            logger.info(
                f"Node.js or Bun not found; diagram {diagram_ref} will be rendered dynamically by viewer.bundle.js."
            )

        # Fallback container for Svelte viewer
        escaped_code = html.escape(code.strip())
        fallback_html = (
            f'<figure class="mermaid-diagram mermaid-fallback" data-engine="client"{id_str}>\n'
            f'  <div class="mermaid-svg-wrapper">\n'
            f'    <pre class="mermaid">\n{escaped_code}\n    </pre>\n'
            f'  </div>{caption_html}\n'
            f'</figure>'
        )
        return fallback_html, True
