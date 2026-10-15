"""
core/engine.py
Pure-Python report generator and modular pipeline orchestrator:
  Stage 1: Pre-processing & Diagram Rendering (beautiful-mermaid via Bun/Node)
  Stage 2: Knowledge Pack Ingestion, Lifecycle & Token Resolution (core/kb/)
  Stage 3: Declarative Theme Resolution & Cascading (core/themes.py)
  Stage 4: Pure-Python Markdown AST Compilation (markdown-it-py + transforms)
  Stage 5: Self-Contained Output Bundling & Chromium PDF Export (core/bundler.py)
"""

import sys
import os
import re
import json
import shutil
import subprocess
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any, Tuple

from core.diagnostics import Colors, Diagnostics, PipelineTimer, DiagnosticMetrics
from core.diagrams import MermaidRenderer
from core.kb import KnowledgeLifecycleManager, KnowledgePack
from core.themes import ThemeResolver, ResolvedTheme
from core.parser import MarkdownParser
from core.bundler import AssetBundler
from core.icons import IconService
from core.i18n import I18nCatalog, resolve_locale
from core.config import PRINT_PDF_SCRIPT

@dataclass
class PipelineConfig:
    input_file: Path
    output_file: Optional[Path] = None
    style: Optional[str] = None
    title: Optional[str] = None
    lang: Optional[str] = None
    toc: bool = True
    toc_depth: int = 3
    number_sections: bool = False
    embed_resources: bool = True
    embed_source: bool = True
    highlight_style: Optional[str] = None
    paged: bool = False
    print_mode: bool = False
    generate_pdf: bool = False
    pdf_engine: Optional[str] = None
    enable_mermaid: bool = True
    auto_nowrap: bool = True
    allow_online: bool = True
    enrich: Optional[bool] = None
    kb_refresh: Optional[str] = None  # None, "incremental", "sources", "force"
    knowledge_path: Optional[Path] = None
    i18n_path: Optional[Path] = None
    toc_levels: Optional[str] = None
    verbose: bool = False
    quiet: bool = False

DISALLOWED_INPUT_EXTENSIONS = {
    ".pdf", ".html", ".htm", ".xhtml", ".docx", ".doc", ".odt",
    ".epub", ".zip", ".tar", ".gz", ".png", ".jpg", ".jpeg",
    ".gif", ".webp", ".svg", ".exe", ".bin", ".wasm", ".pyc"
}

def validate_input_file(input_path: Path) -> None:
    """Validates that the input file exists and is a readable text / Markdown document."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if not input_path.is_file():
        raise ValueError(f"Input path is not a regular file: {input_path}")

    ext = input_path.suffix.lower()
    if ext in DISALLOWED_INPUT_EXTENSIONS:
        raise ValueError(
            f"Unsupported input file format '{ext}' for '{input_path.name}'. "
            f"md-style expects a Markdown or text document (.md, .markdown, .txt)."
        )

    # Inspect first 4096 bytes for binary signatures / null bytes / HTML
    try:
        with open(input_path, "rb") as f:
            chunk = f.read(4096)
    except Exception as e:
        raise ValueError(f"Cannot read input file '{input_path.name}': {e}")

    # 1. Null byte check (standard binary file detection)
    if b"\x00" in chunk:
        raise ValueError(
            f"Input file '{input_path.name}' appears to be a binary file, not a text/markdown document."
        )

    # 2. PDF magic bytes (%PDF-)
    if chunk.startswith(b"%PDF-"):
        raise ValueError(
            f"Input file '{input_path.name}' is a PDF document, not a Markdown document."
        )

    # 3. HTML document detection (if file does not have .md/.markdown extension and begins with HTML doctype/tag)
    if ext not in {".md", ".markdown", ".mdown", ".mkd"}:
        stripped = chunk.lstrip().lower()
        if stripped.startswith(b"<!doctype html") or stripped.startswith(b"<html"):
            raise ValueError(
                f"Input file '{input_path.name}' appears to be raw HTML, not a Markdown document."
            )

class ReportEngine:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.timer = PipelineTimer()
        self.metrics = DiagnosticMetrics()
        Diagnostics.verbose = config.verbose
        self.theme_resolver = ThemeResolver()

    def run(self) -> Path:
        self.timer.start("total")
        # ------------------------------------------------------------------
        # STAGE 1: Document Ingestion & Validation
        # ------------------------------------------------------------------
        self.timer.start("stage1")
        input_file = self.config.input_file.resolve()

        validate_input_file(input_file)

        # Read markdown document
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                raw_content = f.read()
        except Exception as e:
            Diagnostics.error(f"Failed to read {input_file}: {e}")
            sys.exit(1)

        raw_content = self._normalize_nested_containers(raw_content)

        # Extract frontmatter early for configuration
        temp_parser = MarkdownParser()
        cleaned_content, frontmatter = temp_parser.parse_frontmatter(raw_content)

        # Resolve document title
        doc_title = self.config.title or frontmatter.get("title")
        if not doc_title:
            # First h1 match
            h1_match = re.search(r"^#\s+(.+)$", cleaned_content, re.MULTILINE)
            doc_title = h1_match.group(1).strip() if h1_match else input_file.stem

        # Resolve document language & locale
        doc_lang = (self.config.lang or frontmatter.get("lang") or frontmatter.get("language") or "en").strip().lower()
        style_param = self.config.style or frontmatter.get("style") or frontmatter.get("theme") or "forensic"
        catalog = I18nCatalog(
            lang=doc_lang,
            style_family=style_param,
            frontmatter=frontmatter,
            custom_file=self.config.i18n_path
        )

        # Determine target output path
        if not self.config.output_file:
            ext = ".pdf" if self.config.generate_pdf else ".html"
            self.config.output_file = input_file.with_suffix(ext)

        target_html = (
            self.config.output_file
            if not self.config.generate_pdf
            else self.config.output_file.with_suffix(".tmp.html")
        )
        target_html.parent.mkdir(parents=True, exist_ok=True)
        self.timer.stop("stage1")

        if not self.config.quiet and self.config.verbose:
            Diagnostics.info(
                f"Stage 1: Document Ingestion & Validation ({self.timer.get('stage1'):.2f}s)"
            )

        # ------------------------------------------------------------------
        # STAGE 2: Knowledge Pack Ingestion, Lifecycle & Token Resolution
        # ------------------------------------------------------------------
        self.timer.start("stage2")
        kb_manager = KnowledgeLifecycleManager(input_file, catalog=catalog)
        pack = kb_manager.sync(
            raw_content,
            frontmatter=frontmatter,
            refresh_mode=self.config.kb_refresh,
            allow_online=self.config.allow_online
        )
        self.timer.stop("stage2")

        if not self.config.quiet and pack.entities:
            Diagnostics.info(
                f"Stage 2: Knowledge Pack synchronized with {len(pack.entities)} entities ({self.timer.get('stage2'):.2f}s)"
            )
            if self.config.verbose:
                by_type: Dict[str, List[str]] = {}
                for e_id, e in pack.entities.items():
                    t = e.type or "entity"
                    by_type.setdefault(t, []).append(e_id)
                print(f"      ┌─ Knowledge Pack Breakdown ({len(pack.entities)} entities):")
                for t, items in sorted(by_type.items()):
                    sample = ", ".join(items[:5])
                    extra = f" (+{len(items)-5} more)" if len(items) > 5 else ""
                    print(f"      │  • {t.upper()} ({len(items)}): {sample}{extra}")
                print(f"      └────────────────────────────────────────────")

        # ------------------------------------------------------------------
        # STAGE 3: Declarative Theme Resolution & Cascading
        # ------------------------------------------------------------------
        self.timer.start("stage3")
        resolved_theme = self.theme_resolver.resolve(style_param)
        self.timer.stop("stage3")

        if not self.config.quiet:
            chain_str = " -> ".join(resolved_theme.inheritance_chain)
            time_suffix = f" ({self.timer.get('stage3'):.2f}s)" if self.config.verbose else ""
            Diagnostics.info(f"Stage 3: Theme resolved: {resolved_theme.name} [{chain_str}]{time_suffix}")

        if self.config.highlight_style:
            resolved_theme.highlight_style = self.config.highlight_style

        # ------------------------------------------------------------------
        # STAGE 4: Pure-Python Markdown AST Compilation & Transforms
        # ------------------------------------------------------------------
        self.timer.start("stage4")
        parsed_levels = None
        if self.config.toc_levels:
            try:
                parsed_levels = [int(x.strip()) for x in self.config.toc_levels.split(",") if x.strip()]
            except Exception:
                parsed_levels = None

        icon_service = IconService(allow_online=self.config.allow_online)
        parser = MarkdownParser(
            lang=doc_lang,
            catalog=catalog,
            icon_service=icon_service,
            highlight_style=resolved_theme.highlight_style,
            enable_toc=self.config.toc,
            toc_depth=self.config.toc_depth,
            toc_levels=parsed_levels,
            style_family=style_param,
            enable_mermaid=self.config.enable_mermaid,
            theme_name=resolved_theme.name,
        )
        html_fragment, toc, meta = parser.render(
            raw_content,
            knowledge_pack=pack,
            frontmatter=frontmatter
        )

        # Synthesize frontmatter dossier header if appropriate
        if self._should_build_dossier_header(style_param, frontmatter):
            dossier_block = self._build_dossier_header(
                frontmatter, doc_title, catalog, parser=parser, knowledge_pack=pack, style=style_param
            )
            html_fragment = f"{dossier_block}\n{html_fragment}"

        total_diagrams = 0
        if parser.mermaid_renderer:
            total_diagrams += parser.mermaid_renderer.figure_count
        if parser.d2_renderer:
            total_diagrams += parser.d2_renderer.figure_count
        self.metrics.diagrams_rendered = total_diagrams
        if not self.config.quiet:
            if self.config.verbose:
                Diagnostics.info(
                    f"Stage 4: Markdown AST & Transforms compiled ({self.timer.get('stage4'):.2f}s)"
                )
            elif self.metrics.diagrams_rendered > 0:
                Diagnostics.info(
                    f"Stage 4: Processed {self.metrics.diagrams_rendered} diagram(s)"
                )
        self.timer.stop("stage4")

        # ------------------------------------------------------------------
        # STAGE 5: Self-Contained Output Bundling & Chromium PDF Export
        # ------------------------------------------------------------------
        self.timer.start("stage5")
        bundler = AssetBundler(input_file, allow_online=self.config.allow_online)
        complete_html = bundler.assemble(
            html_fragment=html_fragment,
            theme=resolved_theme,
            knowledge_pack=pack,
            catalog=catalog,
            title=doc_title,
            lang=doc_lang,
            paged_mode=self.config.paged,
            print_mode=self.config.print_mode,
            frontmatter=frontmatter,
            raw_markdown=raw_content if self.config.embed_source else None,
            meta_tags={"generator": "md-style v3.0 (pure-python)"}
        )

        with open(target_html, "w", encoding="utf-8") as f:
            f.write(complete_html)

        if self.config.generate_pdf:
            try:
                self._compile_pdf(
                    target_html,
                    self.config.output_file,
                    theme=resolved_theme,
                    catalog=catalog,
                    title=doc_title,
                    frontmatter=frontmatter,
                    bundler=bundler
                )
            finally:
                if target_html.is_file() and target_html != self.config.output_file:
                    target_html.unlink(missing_ok=True)

        self.timer.stop("stage5")
        if not self.config.quiet and self.config.verbose:
            Diagnostics.info(
                f"Stage 5: Output Bundling & Export completed ({self.timer.get('stage5'):.2f}s)"
            )
        total_time = self.timer.stop("total")

        if not self.config.quiet:
            if self.config.verbose:
                self.print_timing_breakdown(total_time)
            Diagnostics.success(
                f"Report generated: {self.config.output_file.resolve()} (Total: {total_time:.2f}s)"
            )

        return self.config.output_file

    def get_stage_timings(self) -> Dict[str, float]:
        """Returns durations for all 5 pipeline stages and total elapsed time."""
        return {
            "stage1": self.timer.get("stage1"),
            "stage2": self.timer.get("stage2"),
            "stage3": self.timer.get("stage3"),
            "stage4": self.timer.get("stage4"),
            "stage5": self.timer.get("stage5"),
            "total": self.timer.get("total"),
        }

    def print_timing_breakdown(self, total_time: float) -> None:
        """Prints a structured 5-stage timing breakdown to stderr."""
        s1 = self.timer.get("stage1")
        s2 = self.timer.get("stage2")
        s3 = self.timer.get("stage3")
        s4 = self.timer.get("stage4")
        s5 = self.timer.get("stage5")
        print("", file=sys.stderr)
        print(f"{Colors.BOLD}Pipeline Timing Breakdown:{Colors.RESET}", file=sys.stderr)
        print(f"  • Stage 1 (Validation & Ingestion):     {s1:6.2f}s", file=sys.stderr)
        print(f"  • Stage 2 (Knowledge Pack Sync):        {s2:6.2f}s", file=sys.stderr)
        print(f"  • Stage 3 (Theme Resolution):           {s3:6.2f}s", file=sys.stderr)
        print(f"  • Stage 4 (Markdown AST & Transforms):  {s4:6.2f}s", file=sys.stderr)
        print(f"  • Stage 5 (Output Bundling & Export):   {s5:6.2f}s", file=sys.stderr)
        print(f"  • Total Compilation Time:               {total_time:6.2f}s", file=sys.stderr)
        print("", file=sys.stderr)

    def _compile_pdf(
        self,
        src_html: Path,
        dst_pdf: Path,
        theme: Optional[ResolvedTheme] = None,
        catalog: Optional[I18nCatalog] = None,
        title: str = "Report",
        frontmatter: Optional[Dict[str, Any]] = None,
        bundler: Optional[AssetBundler] = None
    ):
        """Converts HTML to PDF using high-fidelity Headless Chromium CDP with native headers and footers."""
        # 1. Try modern Node/Bun CDP printer script if available
        runtime = shutil.which("bun") or shutil.which("node")
        if runtime and PRINT_PDF_SCRIPT.is_file():
            print_options: Dict[str, Any] = {}
            if bundler and theme and catalog:
                try:
                    fingerprint_val = getattr(bundler, "fingerprint", "")
                    print_options = bundler.build_cdp_header_footer_templates(
                        theme=theme,
                        catalog=catalog,
                        title=title,
                        frontmatter=frontmatter,
                        fingerprint=fingerprint_val
                    )
                except Exception as ex:
                    Diagnostics.warn(f"Failed to build CDP templates: {ex}")

            Diagnostics.info(f"Generating high-fidelity PDF via {runtime} CDP bridge...")
            cmd = [
                runtime,
                str(PRINT_PDF_SCRIPT),
                str(src_html.resolve()),
                str(dst_pdf.resolve()),
                json.dumps(print_options)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0 and dst_pdf.is_file() and dst_pdf.stat().st_size > 0:
                return
            Diagnostics.warn(f"CDP printer returned code {res.returncode}: {res.stderr.strip() or res.stdout.strip()}")

        # 2. Fallback: Direct headless browser execution
        browsers = ["chromium-browser", "chromium", "google-chrome", "brave-browser", "microsoft-edge"]
        chosen_browser = None
        for b in browsers:
            if shutil.which(b):
                chosen_browser = b
                break

        if chosen_browser:
            Diagnostics.info(f"Generating fallback PDF via headless {chosen_browser}...")
            cmd = [
                chosen_browser,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--run-all-compositor-stages-before-draw",
                "--no-pdf-header-footer",
                f"--print-to-pdf={dst_pdf.resolve()}",
                f"file://{src_html.resolve()}"
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, check=False)
            if res.returncode == 0 and dst_pdf.is_file() and dst_pdf.stat().st_size > 0:
                return
            Diagnostics.warn(f"Browser PDF failed: {res.stderr}")

        if dst_pdf.is_file() and dst_pdf.stat().st_size == 0:
            dst_pdf.unlink(missing_ok=True)

        Diagnostics.error("No suitable Chromium browser found for PDF export.")
        raise RuntimeError(
            "PDF export failed: No suitable Chromium browser found or printer script returned an error."
        )

    def _should_build_dossier_header(self, style: str, frontmatter: Optional[Dict[str, Any]]) -> bool:
        fm = frontmatter or {}
        if fm.get("dossier_header") is False:
            return False
        if fm.get("dossier_header") is True:
            return bool(fm.get("title"))
        is_forensic = "forensic" in (style or "").lower()
        has_meta = any(k in fm for k in ("author", "examiner", "date", "abstract", "subtitle", "case_id", "case"))
        return (is_forensic or has_meta) and bool(fm.get("title"))

    def _build_dossier_header(
        self,
        frontmatter: Optional[Dict[str, Any]],
        title: str,
        catalog: I18nCatalog,
        parser: Optional[Any] = None,
        knowledge_pack: Optional[Any] = None,
        style: str = ""
    ) -> str:
        import html
        fm = frontmatter or {}
        style_val = (
            style
            or (self.config.style if self.config else "")
            or str(fm.get("style") or fm.get("theme") or "")
        )
        if style_val:
            is_forensic = "forensic" in style_val.lower()
        else:
            is_forensic = (
                bool(fm.get("examiner"))
                or bool(re.search(r"\b(?:examiner|vyšetřovatel)\b", str(fm.get("author", "")), re.IGNORECASE))
                or "forensic" in str(title).lower()
                or "forenzní" in str(title).lower()
            )

        report_badge = fm.get("report_badge") or fm.get("report-badge") or fm.get("classification")
        if not report_badge and is_forensic:
            report_badge = (
                catalog.get("forensics.report_title")
                or catalog.get("meta.report_type")
                or "DIGITAL FORENSIC INVESTIGATION REPORT"
            )
        subtitle = fm.get("subtitle", "")
        author = fm.get("author") or fm.get("examiner", "")
        date = fm.get("date", "")
        case_id = fm.get("case_id") or fm.get("case", "")
        abstract = fm.get("abstract", "")

        lines = ['<header id="title-block-header">']
        if report_badge:
            lines.append(f'  <div class="report-badge">{html.escape(str(report_badge))}</div>')
        lines.append(f'  <h1 class="title">{html.escape(str(title))}</h1>')
        if subtitle:
            if parser and hasattr(parser, "md"):
                rendered_sub = parser.md.renderInline(str(subtitle))
                lines.append(f'  <p class="subtitle">{rendered_sub}</p>')
            else:
                lines.append(f'  <p class="subtitle">{html.escape(str(subtitle))}</p>')

        meta_items = []
        if author:
            clean_author = str(author).strip()
            clean_author = re.sub(
                r"^(?:lead\s+examiner|examiner|vyšetřovatel|vedoucí\s+vyšetřovatel|autor|author):\s*",
                "",
                clean_author,
                flags=re.IGNORECASE
            ).strip()
            if is_forensic or fm.get("examiner"):
                author_label = (
                    catalog.get("forensics.examiner")
                    or catalog.get("meta.examiner_label")
                    or catalog.get("meta.author_label")
                    or "Examiner:"
                )
            else:
                author_label = (
                    catalog.get("meta.author_label")
                    or "Author:"
                )
            meta_items.append(f'<p class="author"><span class="meta-label">{html.escape(author_label)}</span> {html.escape(clean_author)}</p>')
        if date:
            date_label = (catalog.get("forensics.date") if is_forensic else None) or catalog.get("meta.date_label") or "Date:"
            meta_items.append(f'<p class="date"><span class="meta-label">{html.escape(date_label)}</span> {html.escape(str(date))}</p>')
        if case_id:
            case_label = catalog.get("forensics.case_id") or catalog.get("meta.case_label") or "Case ID:"
            meta_items.append(f'<p class="case-id"><span class="meta-label">{html.escape(case_label)}</span> {html.escape(str(case_id))}</p>')

        if meta_items:
            lines.append('  <div class="metadata-grid">')
            for mi in meta_items:
                lines.append(f'    {mi}')
            lines.append('  </div>')

        if abstract:
            lines.append('  <div class="abstract">')
            lines.append(f'    <div class="abstract-title">{catalog.get("meta.abstract_title", "EXECUTIVE SUMMARY")}</div>')
            if parser:
                rendered_abs, _, _ = parser.render(str(abstract), knowledge_pack=knowledge_pack)
                lines.append(f'    <div class="abstract-body">{rendered_abs.strip()}</div>')
            else:
                lines.append(f'    <p>{html.escape(str(abstract))}</p>')
            lines.append('  </div>')

        lines.append('</header>\n')
        return "\n".join(lines)

    @staticmethod
    def _normalize_nested_containers(content: str) -> str:
        """Ensures nested Pandoc div containers (::: {...}) have sufficient fence colon length

        so inner containers do not prematurely close outer containers in markdown-it-py.
        """
        lines = content.splitlines()
        container_open_re = re.compile(r"^(:{3,})\s*(\{.*\}|[a-zA-Z0-9_-]+)\s*$")
        container_close_re = re.compile(r"^(:{3,})\s*$")
        containers = []
        open_stack = []
        for idx, line in enumerate(lines):
            m_open = container_open_re.match(line)
            m_close = container_close_re.match(line)
            if m_open:
                open_stack.append((idx, len(m_open.group(1)), m_open.group(2)))
            elif m_close and open_stack:
                start_idx, colons, info = open_stack.pop()
                depth = len(open_stack)
                containers.append((start_idx, idx, depth, colons, info))

        if not containers:
            return content

        colons_map = {}
        for start_idx, close_idx, depth, colons, info in sorted(containers, key=lambda c: c[2], reverse=True):
            children = [c for c in containers if c[0] > start_idx and c[1] < close_idx]
            if children:
                max_child_colons = max(colons_map.get(c[0], c[3]) for c in children)
                req_colons = max_child_colons + 1
                colons_map[start_idx] = req_colons
                colons_map[close_idx] = req_colons

        if not colons_map:
            return content

        new_lines = []
        for idx, line in enumerate(lines):
            if idx in colons_map:
                c_cnt = colons_map[idx]
                m_open = container_open_re.match(line)
                m_close = container_close_re.match(line)
                if m_open:
                    new_lines.append(":" * c_cnt + " " + m_open.group(2))
                elif m_close:
                    new_lines.append(":" * c_cnt)
            else:
                new_lines.append(line)
        return "\n".join(new_lines)
