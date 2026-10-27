"""
core/pipeline/__init__.py
Modular document compilation pipeline.
"""

from core.pipeline.context import PipelineConfig, PipelineContext, validate_input_file
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
    "PipelineConfig",
    "PipelineContext",
    "PipelineBuilder",
    "ReportEngine",
    "SummaryReporter",
    "PipelineStage",
    "Stage1Ingestion",
    "Stage2Knowledge",
    "Stage3Theme",
    "Stage4Compilation",
    "Stage5Export",
    "validate_input_file",
]
