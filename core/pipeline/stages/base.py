"""
core/pipeline/stages/base.py
Abstract base class for document compilation pipeline stages.
"""

from abc import ABC, abstractmethod
from typing import Optional

from core.pipeline.context import PipelineContext


class PipelineStage(ABC):
    """Abstract base class for sequential pipeline stages."""

    name: str = "Stage"
    stage_key: str = "stage"

    @abstractmethod
    def execute(self, context: PipelineContext, status_ctx=None) -> None:
        """Executes stage logic and mutates context accordingly."""
        pass
