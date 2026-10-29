"""
core/pipeline/stages/export.py
Stage 5: Self-Contained Output Bundling, RO-Crate Packaging, and Chromium PDF Export.
"""

import json
import shutil
import subprocess
from pathlib import Path
from typing import Optional, Dict, Any

from core.diagnostics import Diagnostics
from core.bundler import AssetBundler
from core.config import PRINT_PDF_SCRIPT
from core.pipeline.stages.base import PipelineStage
from core.pipeline.context import PipelineContext


class Stage5Export(PipelineStage):
    """Bundles assets, builds standalone HTML, compiles PDF, or packages RO-Crate."""

    name = "Stage 5: Output Bundling & Export"
    stage_key = "stage5"

    def execute(self, context: PipelineContext, status_ctx=None) -> None:
        if status_ctx:
            status_ctx.update("[bold cyan]Stage 5/5: Bundling Self-Contained Output...[/bold cyan]")

        context.timer.start(self.stage_key)
        input_file = context.config.input_file.resolve()

        # Resolve font subsets and diagram font deduplication
        from core.fonts import resolve_font_subsets

        fm = context.frontmatter or {}
        subsets = resolve_font_subsets(
            lang=context.doc_lang,
            font_subsets_opt=context.config.font_subsets,
            all_fonts=context.config.all_fonts,
            frontmatter_subsets=fm.get("font_subsets"),
        )

        dedup_diagram_fonts = True
        if context.config.embed_diagram_fonts:
            dedup_diagram_fonts = False
        elif "embed_diagram_fonts" in fm:
            dedup_diagram_fonts = not bool(fm.get("embed_diagram_fonts"))
        elif "dedup_diagram_fonts" in fm:
            dedup_diagram_fonts = bool(fm.get("dedup_diagram_fonts"))

        bundler = AssetBundler(
            input_file,
            allow_online=context.config.allow_online,
            subsets=subsets,
            dedup_diagram_fonts=dedup_diagram_fonts,
        )

        # Auto-discover annotations: frontmatter takes precedence, then sidecar <doc>.annotations.json
        annotations_data = context.frontmatter.get("annotations")
        if not annotations_data:
            sidecar_json = input_file.with_suffix(".annotations.json")
            if sidecar_json.is_file():
                try:
                    with open(sidecar_json, "r", encoding="utf-8") as f:
                        raw_ann = json.load(f)
                        if isinstance(raw_ann, dict) and "annotations" in raw_ann:
                            annotations_data = raw_ann["annotations"]
                        elif isinstance(raw_ann, list):
                            annotations_data = raw_ann
                except Exception as e:
                    Diagnostics.warn(f"Failed to read sidecar annotations {sidecar_json}: {e}")

        complete_html = bundler.assemble(
            html_fragment=context.html_fragment,
            theme=context.resolved_theme,
            knowledge_pack=context.pack,
            catalog=context.catalog,
            title=context.doc_title,
            lang=context.doc_lang,
            paged_mode=context.config.paged,
            print_mode=context.config.print_mode,
            frontmatter=context.frontmatter,
            raw_markdown=context.raw_content if context.config.embed_source else None,
            meta_tags={"generator": "md-style v3.0 (pure-python)"},
            annotations=annotations_data,
            interactive_viewer=context.config.interactive_viewer
        )
        context.bundled_html = complete_html

        target_html = context.target_html
        with open(target_html, "w", encoding="utf-8") as f:
            f.write(complete_html)

        if context.config.generate_pdf:
            try:
                self.compile_pdf(
                    src_html=target_html,
                    dst_pdf=context.config.output_file,
                    theme=context.resolved_theme,
                    catalog=context.catalog,
                    title=context.doc_title,
                    frontmatter=context.frontmatter,
                    bundler=bundler
                )
            finally:
                if target_html.is_file() and target_html != context.config.output_file:
                    target_html.unlink(missing_ok=True)
        elif context.is_crate:
            try:
                from core.crate import ROCrateBuilder
                crate_builder = ROCrateBuilder(
                    title=context.doc_title,
                    description=str(context.frontmatter.get("description") or context.frontmatter.get("abstract") or f"RO-Crate report archive for {context.doc_title}"),
                    author=str(context.frontmatter.get("author") or context.frontmatter.get("examiner") or ""),
                    date_published=str(context.frontmatter.get("date")) if context.frontmatter.get("date") else None
                )
                crate_builder.add_file(
                    target_html,
                    rel_path="report.html",
                    name="Compiled Interactive Report",
                    encoding_format="text/html",
                    description="Self-contained compiled report with embedded theme and viewer"
                )
                crate_builder.add_file(
                    input_file,
                    rel_path="report.md",
                    name="Markdown Source Document",
                    encoding_format="text/markdown",
                    description="Original authoring Markdown document with frontmatter"
                )
                if context.pack:
                    crate_builder.add_knowledge_pack(context.pack, rel_path="report.kb.json")
                if context.config.evidence_path:
                    ev_path = Path(context.config.evidence_path)
                    crate_builder.add_evidence_dir(ev_path, target_prefix="evidence")
                crate_builder.build_zip(context.config.output_file)
            finally:
                if target_html.is_file() and target_html != context.config.output_file:
                    target_html.unlink(missing_ok=True)

        context.timer.stop(self.stage_key)
        if not context.config.quiet and context.config.verbose:
            Diagnostics.info(
                f"Stage 5: Output Bundling & Export completed ({context.timer.get(self.stage_key):.2f}s)"
            )

    @staticmethod
    def compile_pdf(
        src_html: Path,
        dst_pdf: Path,
        theme: Optional[Any] = None,
        catalog: Optional[Any] = None,
        title: str = "Report",
        frontmatter: Optional[Dict[str, Any]] = None,
        bundler: Optional[AssetBundler] = None
    ) -> None:
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
            import tempfile
            chrome_tmp = tempfile.mkdtemp(prefix="md-style-chrome-")
            Diagnostics.info(f"Generating fallback PDF via headless {chosen_browser}...")
            cmd = [
                chosen_browser,
                "--headless",
                "--disable-gpu",
                "--no-sandbox",
                "--disable-dev-shm-usage",
                f"--user-data-dir={chrome_tmp}",
                "--run-all-compositor-stages-before-draw",
                "--no-pdf-header-footer",
                f"--print-to-pdf={dst_pdf.resolve()}",
                f"file://{src_html.resolve()}"
            ]
            try:
                res = subprocess.run(cmd, capture_output=True, text=True, check=False)
                if res.returncode == 0 and dst_pdf.is_file() and dst_pdf.stat().st_size > 0:
                    return
                Diagnostics.warn(f"Browser PDF failed: {res.stderr}")
            finally:
                shutil.rmtree(chrome_tmp, ignore_errors=True)

        if dst_pdf.is_file() and dst_pdf.stat().st_size == 0:
            dst_pdf.unlink(missing_ok=True)

        Diagnostics.error("No suitable Chromium browser found for PDF export.")
        raise RuntimeError(
            "PDF export failed: No suitable Chromium browser found or printer script returned an error."
        )
