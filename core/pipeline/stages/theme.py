"""
core/pipeline/stages/theme.py
Stage 3: Declarative Theme Resolution and Inheritance Cascading.
"""

from core.diagnostics import Diagnostics
from core.themes import ThemeResolver
from core.pipeline.stages.base import PipelineStage
from core.pipeline.context import PipelineContext


class Stage3Theme(PipelineStage):
    """Resolves declarative theme cascade, feature flags, and typography."""

    name = "Stage 3: Theme Resolution"
    stage_key = "stage3"

    def __init__(self, theme_resolver: ThemeResolver = None):
        self.theme_resolver = theme_resolver or ThemeResolver()

    def execute(self, context: PipelineContext, status_ctx=None) -> None:
        if status_ctx:
            status_ctx.update(f"[bold cyan]Stage 3/5: Resolving Theme ({context.style_param})...[/bold cyan]")

        context.timer.start(self.stage_key)
        resolved_theme = self.theme_resolver.resolve(context.style_param)
        context.resolved_theme = resolved_theme
        context.timer.stop(self.stage_key)

        if not context.config.quiet:
            chain_str = " -> ".join(resolved_theme.inheritance_chain)
            time_suffix = f" ({context.timer.get(self.stage_key):.2f}s)" if context.config.verbose else ""
            Diagnostics.info(f"Stage 3: Theme resolved: {resolved_theme.name} [{chain_str}]{time_suffix}")

        if context.config.highlight_style:
            resolved_theme.highlight_style = context.config.highlight_style
