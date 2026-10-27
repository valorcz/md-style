"""
core/pipeline/builder.py
Fluent Builder pattern for assembling and configuring the compilation pipeline.
"""

from pathlib import Path
from typing import Optional, List

from core.pipeline.context import PipelineConfig, PipelineContext
from core.pipeline.stages import (
    PipelineStage,
    Stage1Ingestion,
    Stage2Knowledge,
    Stage3Theme,
    Stage4Compilation,
    Stage5Export,
)


class PipelineBuilder:
    """Fluent builder for constructing PipelineConfig and sequential PipelineStages."""

    def __init__(self, input_file: Optional[Path] = None):
        self._input_file: Optional[Path] = input_file
        self._output_file: Optional[Path] = None
        self._style: Optional[str] = None
        self._title: Optional[str] = None
        self._lang: Optional[str] = None
        self._toc: Optional[bool] = None
        self._toc_depth: int = 3
        self._number_sections: bool = False
        self._embed_resources: bool = True
        self._embed_source: bool = True
        self._highlight_style: Optional[str] = None
        self._paged: bool = False
        self._print_mode: bool = False
        self._generate_pdf: bool = False
        self._pdf_engine: Optional[str] = None
        self._generate_crate: bool = False
        self._evidence_path: Optional[Path] = None
        self._interactive_viewer: Optional[bool] = None
        self._enable_mermaid: bool = True
        self._auto_nowrap: bool = True
        self._allow_online: bool = True
        self._enrich: Optional[bool] = None
        self._kb_refresh: Optional[str] = None
        self._knowledge_path: Optional[Path] = None
        self._i18n_path: Optional[Path] = None
        self._toc_levels: Optional[str] = None
        self._verbose: bool = False
        self._quiet: bool = False

        self._custom_stages: Optional[List[PipelineStage]] = None

    def with_input(self, input_file: Path) -> "PipelineBuilder":
        self._input_file = input_file
        return self

    def with_output(self, output_file: Path) -> "PipelineBuilder":
        self._output_file = output_file
        return self

    def with_style(self, style: str) -> "PipelineBuilder":
        self._style = style
        return self

    def with_title(self, title: str) -> "PipelineBuilder":
        self._title = title
        return self

    def with_lang(self, lang: str) -> "PipelineBuilder":
        self._lang = lang
        return self

    def with_toc(self, enabled: bool = True, depth: int = 3, levels: Optional[str] = None) -> "PipelineBuilder":
        self._toc = enabled
        self._toc_depth = depth
        self._toc_levels = levels
        return self

    def with_pdf(self, enabled: bool = True, engine: Optional[str] = None) -> "PipelineBuilder":
        self._generate_pdf = enabled
        self._pdf_engine = engine
        return self

    def with_crate(self, enabled: bool = True, evidence_path: Optional[Path] = None) -> "PipelineBuilder":
        self._generate_crate = enabled
        self._evidence_path = evidence_path
        return self

    def with_online(self, allow_online: bool = True) -> "PipelineBuilder":
        self._allow_online = allow_online
        return self

    def with_kb_refresh(self, mode: str) -> "PipelineBuilder":
        self._kb_refresh = mode
        return self

    def with_diagnostics(self, verbose: bool = False, quiet: bool = False) -> "PipelineBuilder":
        self._verbose = verbose
        self._quiet = quiet
        return self

    def with_custom_stages(self, stages: List[PipelineStage]) -> "PipelineBuilder":
        self._custom_stages = stages
        return self

    def build_config(self) -> PipelineConfig:
        if not self._input_file:
            raise ValueError("Input file must be specified in PipelineBuilder.")
        return PipelineConfig(
            input_file=self._input_file,
            output_file=self._output_file,
            style=self._style,
            title=self._title,
            lang=self._lang,
            toc=self._toc,
            toc_depth=self._toc_depth,
            number_sections=self._number_sections,
            embed_resources=self._embed_resources,
            embed_source=self._embed_source,
            highlight_style=self._highlight_style,
            paged=self._paged,
            print_mode=self._print_mode,
            generate_pdf=self._generate_pdf,
            pdf_engine=self._pdf_engine,
            generate_crate=self._generate_crate,
            evidence_path=self._evidence_path,
            interactive_viewer=self._interactive_viewer,
            enable_mermaid=self._enable_mermaid,
            auto_nowrap=self._auto_nowrap,
            allow_online=self._allow_online,
            enrich=self._enrich,
            kb_refresh=self._kb_refresh,
            knowledge_path=self._knowledge_path,
            i18n_path=self._i18n_path,
            toc_levels=self._toc_levels,
            verbose=self._verbose,
            quiet=self._quiet,
        )

    def default_stages(self) -> List[PipelineStage]:
        return [
            Stage1Ingestion(),
            Stage2Knowledge(),
            Stage3Theme(),
            Stage4Compilation(),
            Stage5Export(),
        ]
