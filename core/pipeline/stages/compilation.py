"""
core/pipeline/stages/compilation.py
Stage 4: Markdown AST Compilation, Transforms, and Diagram Rendering.
"""

import re
import html
from typing import Optional, Dict, Any, List

from core.diagnostics import Diagnostics
from core.icons import IconService
from core.parser import MarkdownParser
from core.i18n import I18nCatalog
from core.pipeline.stages.base import PipelineStage
from core.pipeline.context import PipelineContext


class Stage4Compilation(PipelineStage):
    """Compiles Markdown tokens into HTML with callouts, tables, diagrams, and figures."""

    name = "Stage 4: AST Compilation & Diagram Processing"
    stage_key = "stage4"

    @staticmethod
    def should_build_dossier_header(style: str, frontmatter: Optional[Dict[str, Any]]) -> bool:
        fm = frontmatter or {}
        if fm.get("dossier_header") is False:
            return False
        if fm.get("dossier_header") is True:
            return bool(fm.get("title"))
        is_forensic = "forensic" in (style or "").lower()
        has_meta = any(k in fm for k in ("author", "examiner", "date", "abstract", "subtitle", "case_id", "case"))
        return (is_forensic or has_meta) and bool(fm.get("title"))

    @staticmethod
    def build_dossier_header(
        frontmatter: Optional[Dict[str, Any]],
        title: str,
        catalog: I18nCatalog,
        parser: Optional[Any] = None,
        knowledge_pack: Optional[Any] = None,
        style: str = ""
    ) -> str:
        fm = frontmatter or {}
        style_val = (
            style
            or str(fm.get("style") or fm.get("theme") or "")
        )
        if style_val:
            is_forensic = "forensic" in style_val.lower()
            is_academic = "academic" in style_val.lower() or "lecture" in style_val.lower() or "teaching" in style_val.lower()
        else:
            is_forensic = (
                bool(fm.get("examiner"))
                or bool(re.search(r"\b(?:examiner|vyšetřovatel)\b", str(fm.get("author", "")), re.IGNORECASE))
                or "forensic" in str(title).lower()
                or "forenzní" in str(title).lower()
            )
            is_academic = bool(fm.get("course") or fm.get("lecture"))

        report_badge = fm.get("report_badge") or fm.get("report-badge") or fm.get("classification")
        if not report_badge and fm.get("course"):
            course_val = str(fm.get("course"))
            lecture_num = fm.get("lecture")
            if lecture_num:
                report_badge = f"{course_val} // Lecture {lecture_num}"
            else:
                report_badge = course_val
        elif not report_badge and is_forensic:
            report_badge = (
                catalog.get("forensics.report_title")
                or catalog.get("meta.report_type")
                or "DIGITAL FORENSIC INVESTIGATION REPORT"
            )

        subtitle = fm.get("subtitle", "")
        author = fm.get("author") or fm.get("examiner", "") or fm.get("instructor", "")
        date = fm.get("date", "")
        term = fm.get("term") or fm.get("semester", "")
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
        if term:
            term_label = catalog.get("meta.term_label") or "Term:"
            meta_items.append(f'<p class="term"><span class="meta-label">{html.escape(term_label)}</span> {html.escape(str(term))}</p>')
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
            default_abs_title = "LECTURE OVERVIEW" if is_academic else "EXECUTIVE SUMMARY"
            lines.append(f'    <div class="abstract-title">{catalog.get("meta.abstract_title", default_abs_title)}</div>')
            if parser:
                rendered_abs, _, _ = parser.render(str(abstract), knowledge_pack=knowledge_pack)
                lines.append(f'    <div class="abstract-body">{rendered_abs.strip()}</div>')
            else:
                lines.append(f'    <div class="abstract-body"><p>{html.escape(str(abstract))}</p></div>')
            lines.append('  </div>')

        lines.append('</header>\n')
        return "\n".join(lines)

    def execute(self, context: PipelineContext, status_ctx=None) -> None:
        if status_ctx:
            status_ctx.update("[bold cyan]Stage 4/5: Compiling Markdown AST & Diagrams...[/bold cyan]")

        context.timer.start(self.stage_key)
        parsed_levels = None
        if context.config.toc_levels:
            try:
                parsed_levels = [int(x.strip()) for x in context.config.toc_levels.split(",") if x.strip()]
            except Exception:
                parsed_levels = None

        resolved_theme = context.resolved_theme
        theme_toc = resolved_theme.features.get("auto_toc") if resolved_theme else None
        if theme_toc is None and resolved_theme:
            theme_toc = resolved_theme.features.get("toc", True)

        fm_toc = context.frontmatter.get("toc")
        if context.config.toc is not None:
            resolved_enable_toc = context.config.toc
        elif fm_toc is not None:
            if isinstance(fm_toc, str):
                resolved_enable_toc = fm_toc.strip().lower() not in ("false", "no", "off", "0", "disable", "disabled")
            else:
                resolved_enable_toc = bool(fm_toc)
        else:
            resolved_enable_toc = bool(theme_toc)

        icon_service = IconService(allow_online=context.config.allow_online)
        parser = MarkdownParser(
            lang=context.doc_lang,
            catalog=context.catalog,
            icon_service=icon_service,
            highlight_style=resolved_theme.highlight_style if resolved_theme else None,
            enable_toc=resolved_enable_toc,
            toc_depth=context.config.toc_depth,
            toc_levels=parsed_levels,
            style_family=context.style_param,
            enable_mermaid=context.config.enable_mermaid,
            theme_name=resolved_theme.name if resolved_theme else "base",
        )

        html_fragment, toc, meta = parser.render(
            context.raw_content,
            knowledge_pack=context.pack,
            frontmatter=context.frontmatter
        )

        # Synthesize frontmatter dossier header if appropriate
        if self.should_build_dossier_header(context.style_param, context.frontmatter):
            dossier_block = self.build_dossier_header(
                context.frontmatter,
                context.doc_title,
                context.catalog,
                parser=parser,
                knowledge_pack=context.pack,
                style=context.style_param
            )
            html_fragment = f"{dossier_block}\n{html_fragment}"

        total_diagrams = parser.figure_manager.count if hasattr(parser, "figure_manager") else 0
        context.metrics.diagrams_rendered = total_diagrams
        context.diagram_count = total_diagrams
        context.html_fragment = html_fragment

        if not context.config.quiet:
            if context.config.verbose:
                Diagnostics.info(
                    f"Stage 4: Markdown AST & Transforms compiled ({context.timer.get(self.stage_key):.2f}s)"
                )
            elif context.metrics.diagrams_rendered > 0:
                Diagnostics.info(
                    f"Stage 4: Processed {context.metrics.diagrams_rendered} diagram(s)"
                )
        context.timer.stop(self.stage_key)
