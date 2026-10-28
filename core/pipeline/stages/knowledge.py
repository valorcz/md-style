"""
core/pipeline/stages/knowledge.py
Stage 2: Knowledge Pack Ingestion, Lifecycle Synchronization, and Token Resolution.
"""

from core.diagnostics import Diagnostics
from core.kb import KnowledgeLifecycleManager
from core.pipeline.stages.base import PipelineStage
from core.pipeline.context import PipelineContext
from core.pipeline.reporter import SummaryReporter


class Stage2Knowledge(PipelineStage):
    """Discovers entities, synchronizes Knowledge Pack, and resolves tokens."""

    name = "Stage 2: Knowledge Pack Ingestion & Lifecycle"
    stage_key = "stage2"

    def execute(self, context: PipelineContext, status_ctx=None) -> None:
        if status_ctx:
            status_ctx.update("[bold cyan]Stage 2/5: Synchronizing Knowledge Pack & Resolving Tokens...[/bold cyan]")

        context.timer.start(self.stage_key)
        input_file = context.config.input_file.resolve()

        kb_manager = KnowledgeLifecycleManager(input_file, catalog=context.catalog)
        pack = kb_manager.sync(
            context.raw_content,
            frontmatter=context.frontmatter,
            refresh_mode=context.config.kb_refresh,
            allow_online=context.config.allow_online
        )
        context.pack = pack
        context.timer.stop(self.stage_key)

        if not context.config.quiet and pack.entities:
            Diagnostics.info(
                f"Stage 2: Knowledge Pack synchronized with {len(pack.entities)} entities ({context.timer.get(self.stage_key):.2f}s)"
            )
            if context.config.verbose:
                SummaryReporter.render_kb_inventory(context)
