"""
core/engine.py
Modular pipeline coordinator and public facade for document compilation.
Re-exports ReportEngine, PipelineConfig, and PipelineBuilder from core.pipeline.
"""

from core.pipeline.context import (
    PipelineConfig,
    PipelineContext,
    validate_input_file,
    DISALLOWED_INPUT_EXTENSIONS,
)
from core.pipeline.builder import PipelineBuilder
from core.pipeline.engine import ReportEngine
from core.pipeline.reporter import SummaryReporter
from core.pipeline.stages import (
    PipelineStage,
    Stage1Ingestion,
    Stage2Knowledge,
    Stage3Theme,
    Stage4Compilation,
    Stage5Export,
)

__all__ = [
    "ReportEngine",
    "PipelineConfig",
    "PipelineContext",
    "PipelineBuilder",
    "SummaryReporter",
    "PipelineStage",
    "Stage1Ingestion",
    "Stage2Knowledge",
    "Stage3Theme",
    "Stage4Compilation",
    "Stage5Export",
    "validate_input_file",
    "DISALLOWED_INPUT_EXTENSIONS",
]
