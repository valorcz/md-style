"""
core/pipeline/stages/ingestion.py
Stage 1: Document Ingestion, Container Normalization, and Metadata Resolution.
"""

import sys
import re
from pathlib import Path
from typing import Dict, Any

from core.diagnostics import Diagnostics
from core.parser import MarkdownParser
from core.i18n import I18nCatalog
from core.pipeline.stages.base import PipelineStage
from core.pipeline.context import PipelineContext, validate_input_file


class Stage1Ingestion(PipelineStage):
    """Ingests Markdown text, normalizes nested blocks, and extracts metadata/locale."""

    name = "Stage 1: Document Ingestion & Validation"
    stage_key = "stage1"

    @staticmethod
    def normalize_nested_containers(content: str) -> str:
        """Ensures nested container fences (::: {...}) have sufficient colon length

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
                colons = ":" * colons_map[idx]
                m_open = container_open_re.match(line)
                if m_open:
                    new_lines.append(f"{colons} {m_open.group(2)}")
                else:
                    new_lines.append(colons)
            else:
                new_lines.append(line)

        return "\n".join(new_lines)

    def execute(self, context: PipelineContext, status_ctx=None) -> None:
        context.timer.start(self.stage_key)
        input_file = context.config.input_file.resolve()

        validate_input_file(input_file)

        try:
            with open(input_file, "r", encoding="utf-8") as f:
                raw_content = f.read()
        except Exception as e:
            Diagnostics.error(f"Failed to read {input_file}: {e}")
            sys.exit(1)

        raw_content = self.normalize_nested_containers(raw_content)
        context.raw_content = raw_content

        # Extract frontmatter
        temp_parser = MarkdownParser()
        cleaned_content, frontmatter = temp_parser.parse_frontmatter(raw_content)
        context.cleaned_content = cleaned_content
        context.frontmatter = frontmatter

        # Resolve document title
        doc_title = context.config.title or frontmatter.get("title")
        if not doc_title:
            h1_match = re.search(r"^#\s+(.+)$", cleaned_content, re.MULTILINE)
            doc_title = h1_match.group(1).strip() if h1_match else input_file.stem
        context.doc_title = doc_title

        # Resolve language & locale
        doc_lang = (context.config.lang or frontmatter.get("lang") or frontmatter.get("language") or "en").strip().lower()
        context.doc_lang = doc_lang
        style_param = context.config.style or frontmatter.get("style") or frontmatter.get("theme") or "forensic"
        context.style_param = style_param

        context.catalog = I18nCatalog(
            lang=doc_lang,
            style_family=style_param,
            frontmatter=frontmatter,
            custom_file=context.config.i18n_path
        )

        # Output target resolution
        is_crate = (
            context.config.generate_crate
            or (context.config.output_file and str(context.config.output_file).lower().endswith((".zip", ".crate.zip")))
        )
        context.is_crate = is_crate

        if not context.config.output_file:
            if is_crate:
                ext = ".crate.zip"
            elif context.config.generate_pdf:
                ext = ".pdf"
            else:
                ext = ".html"
            context.config.output_file = input_file.with_suffix(ext)

        context.final_output_file = context.config.output_file
        target_html = (
            context.config.output_file.with_suffix(".tmp.html")
            if (context.config.generate_pdf or is_crate)
            else context.config.output_file
        )
        target_html.parent.mkdir(parents=True, exist_ok=True)
        context.target_html = target_html

        context.timer.stop(self.stage_key)
        if not context.config.quiet and context.config.verbose:
            Diagnostics.info(
                f"{self.name} ({context.timer.get(self.stage_key):.2f}s)"
            )
