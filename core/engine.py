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
from core.i18n import I18nCatalog, resolve_locale

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
    highlight_style: str = "kate"
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

class ReportEngine:
    def __init__(self, config: PipelineConfig):
        self.config = config
        self.timer = PipelineTimer()
        self.metrics = DiagnosticMetrics()
        Diagnostics.verbose = config.verbose
        self.theme_resolver = ThemeResolver()

    def run(self) -> Path:
        self.timer.start("total")
        input_file = self.config.input_file.resolve()

        if not input_file.is_file():
            Diagnostics.error(f"Input file not found: {input_file}")
            sys.exit(1)

        # Read markdown document
        try:
            with open(input_file, "r", encoding="utf-8") as f:
                raw_content = f.read()
        except Exception as e:
            Diagnostics.error(f"Failed to read {input_file}: {e}")
            sys.exit(1)

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
        style_param = self.config.style or frontmatter.get("style") or frontmatter.get("theme") or "base"
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

        # ------------------------------------------------------------------
        # STAGE 1: Document Ingestion & Validation
        # ------------------------------------------------------------------
        self.timer.start("stage1")
        self.timer.stop("stage1")

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
            Diagnostics.info(f"Stage 3: Theme resolved: {resolved_theme.name} [{chain_str}]")

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

        parser = MarkdownParser(
            lang=doc_lang,
            catalog=catalog,
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
            dossier_block = self._build_dossier_header(frontmatter, doc_title, catalog)
            html_fragment = f"{dossier_block}\n{html_fragment}"

        if parser.mermaid_renderer:
            self.metrics.diagrams_rendered = parser.mermaid_renderer.figure_count
            if not self.config.quiet and self.metrics.diagrams_rendered > 0:
                Diagnostics.info(
                    f"Stage 4: Processed {self.metrics.diagrams_rendered} Mermaid diagram(s)"
                )
        self.timer.stop("stage4")

        # ------------------------------------------------------------------
        # STAGE 5: Self-Contained Output Bundling & Chromium PDF Export
        # ------------------------------------------------------------------
        self.timer.start("stage5")
        bundler = AssetBundler(input_file)
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
            self._compile_pdf(target_html, self.config.output_file)
            if target_html.is_file() and target_html != self.config.output_file:
                target_html.unlink(missing_ok=True)

        self.timer.stop("stage5")
        total_time = self.timer.stop("total")

        if not self.config.quiet:
            Diagnostics.success(
                f"Report generated: {self.config.output_file.resolve()} (Total: {total_time:.2f}s)"
            )

        return self.config.output_file

    def _compile_pdf(self, src_html: Path, dst_pdf: Path):
        """Converts HTML to PDF using Headless Chrome/Chromium."""
        browsers = ["chromium-browser", "chromium", "google-chrome", "brave-browser", "microsoft-edge"]
        chosen_browser = None
        for b in browsers:
            if shutil.which(b):
                chosen_browser = b
                break

        if chosen_browser:
            Diagnostics.info(f"Generating PDF via headless {chosen_browser}...")
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
            if res.returncode == 0:
                return
            Diagnostics.warn(f"Browser PDF failed: {res.stderr}")

        Diagnostics.error("No suitable Chromium browser found for PDF export.")

    def _should_build_dossier_header(self, style: str, frontmatter: Optional[Dict[str, Any]]) -> bool:
        fm = frontmatter or {}
        if fm.get("dossier_header") is False:
            return False
        is_forensic = "forensic" in (style or "").lower()
        has_meta = any(k in fm for k in ("author", "examiner", "date", "abstract", "subtitle", "case_id", "case"))
        return (is_forensic or has_meta) and bool(fm.get("title"))

    def _build_dossier_header(self, frontmatter: Optional[Dict[str, Any]], title: str, catalog: I18nCatalog) -> str:
        import html
        fm = frontmatter or {}
        report_badge = (
            fm.get("report_badge")
            or fm.get("report-badge")
            or fm.get("classification")
            or catalog.get("forensics.report_title")
            or catalog.get("meta.report_type")
            or "DIGITAL FORENSIC INVESTIGATION REPORT"
        )
        subtitle = fm.get("subtitle", "")
        author = fm.get("author") or fm.get("examiner", "")
        date = fm.get("date", "")
        case_id = fm.get("case_id") or fm.get("case", "")
        abstract = fm.get("abstract", "")

        lines = ['<header id="title-block-header">']
        lines.append(f'  <div class="report-badge">{html.escape(str(report_badge))}</div>')
        lines.append(f'  <h1 class="title">{html.escape(str(title))}</h1>')
        if subtitle:
            lines.append(f'  <p class="subtitle">{html.escape(str(subtitle))}</p>')

        meta_items = []
        if author:
            meta_items.append(f'<p class="author"><span class="meta-label">{catalog.get("forensics.examiner", "Examiner:")}</span> {html.escape(str(author))}</p>')
        if date:
            meta_items.append(f'<p class="date"><span class="meta-label">{catalog.get("forensics.date", "Date:")}</span> {html.escape(str(date))}</p>')
        if case_id:
            meta_items.append(f'<p class="case-id"><span class="meta-label">Case ID:</span> {html.escape(str(case_id))}</p>')

        if meta_items:
            lines.append('  <div class="metadata-grid">')
            for mi in meta_items:
                lines.append(f'    {mi}')
            lines.append('  </div>')

        if abstract:
            lines.append('  <div class="abstract">')
            lines.append(f'    <div class="abstract-title">{catalog.get("meta.abstract_title", "EXECUTIVE SUMMARY")}</div>')
            lines.append(f'    <p>{html.escape(str(abstract))}</p>')
            lines.append('  </div>')

        lines.append('</header>\n')
        return "\n".join(lines)
