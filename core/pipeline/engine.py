"""
core/pipeline/engine.py
ReportEngine orchestrator executing the 5-stage compilation pipeline.
"""

from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.table import Table
from rich.panel import Panel
from rich import box

from core.diagnostics import Diagnostics, PipelineTimer, DiagnosticMetrics, stderr_console
from core.themes import ThemeResolver, ResolvedTheme
from core.kb.models import KnowledgePack
from core.i18n import I18nCatalog
from core.pipeline.context import PipelineConfig, PipelineContext, validate_input_file
from core.pipeline.builder import PipelineBuilder
from core.pipeline.stages import (
    PipelineStage,
    Stage1Ingestion,
    Stage2Knowledge,
    Stage3Theme,
    Stage4Compilation,
    Stage5Export,
)


class ReportEngine:
    """Orchestrates the 5-stage document compilation pipeline."""

    def __init__(self, config: PipelineConfig, stages: Optional[List[PipelineStage]] = None):
        self.config = config
        self.timer = PipelineTimer()
        self.metrics = DiagnosticMetrics()
        Diagnostics.verbose = config.verbose
        self.theme_resolver = ThemeResolver()
        self.stages = stages or [
            Stage1Ingestion(),
            Stage2Knowledge(),
            Stage3Theme(self.theme_resolver),
            Stage4Compilation(),
            Stage5Export(),
        ]

    def run(self) -> Path:
        self.timer.start("total")
        use_status = not self.config.quiet and not self.config.verbose and getattr(stderr_console, "is_terminal", False)
        status_ctx = stderr_console.status("[bold cyan]Stage 1/5: Document Ingestion & Validation...[/bold cyan]", spinner="dots") if use_status else None
        if status_ctx:
            status_ctx.start()

        try:
            return self._run_pipeline(status_ctx)
        finally:
            if status_ctx:
                try:
                    status_ctx.stop()
                except Exception:
                    pass

    def _run_pipeline(self, status_ctx=None) -> Path:
        context = PipelineContext(
            config=self.config,
            timer=self.timer,
            metrics=self.metrics
        )

        for stage in self.stages:
            stage.execute(context, status_ctx=status_ctx)

        total_time = self.timer.stop("total")
        if status_ctx:
            try:
                status_ctx.stop()
            except Exception:
                pass
            status_ctx = None

        if not self.config.quiet:
            if self.config.verbose:
                self.print_timing_breakdown(total_time)
            self.print_compilation_summary(
                output_file=context.final_output_file,
                total_time=total_time,
                theme_name=context.resolved_theme.name if context.resolved_theme else "base",
                pack=context.pack,
                diagrams_count=self.metrics.diagrams_rendered,
                is_pdf=self.config.generate_pdf,
                is_crate=context.is_crate
            )
            Diagnostics.success(
                f"Report generated: {context.final_output_file.resolve()} (Total: {total_time:.2f}s)"
            )

        return context.final_output_file

    def get_stage_timings(self) -> Dict[str, float]:
        """Returns durations for all 5 pipeline stages and total elapsed time."""
        return {
            "stage1": self.timer.get("stage1"),
            "stage2": self.timer.get("stage2"),
            "stage3": self.timer.get("stage3"),
            "stage4": self.timer.get("stage4"),
            "stage5": self.timer.get("stage5"),
            "total": self.timer.get("total"),
        }

    def print_timing_breakdown(self, total_time: float) -> None:
        """Prints a structured 5-stage timing breakdown to stderr."""
        s1 = self.timer.get("stage1")
        s2 = self.timer.get("stage2")
        s3 = self.timer.get("stage3")
        s4 = self.timer.get("stage4")
        s5 = self.timer.get("stage5")

        table = Table(
            title="Pipeline Timing Breakdown:",
            box=box.ROUNDED,
            header_style="bold magenta",
            show_header=True
        )
        table.add_column("Pipeline Stage", style="bold cyan")
        table.add_column("Description", style="white")
        table.add_column("Duration", justify="right", style="bold yellow")

        table.add_row("Stage 1", "Stage 1 (Validation & Ingestion):", f"{s1:6.2f}s")
        table.add_row("Stage 2", "Stage 2 (Knowledge Pack Sync):", f"{s2:6.2f}s")
        table.add_row("Stage 3", "Stage 3 (Theme Resolution):", f"{s3:6.2f}s")
        table.add_row("Stage 4", "Stage 4 (Markdown AST & Transforms):", f"{s4:6.2f}s")
        table.add_row("Stage 5", "Stage 5 (Output Bundling & Export):", f"{s5:6.2f}s")
        table.add_section()
        table.add_row("Total", "Total Compilation Time:", f"{total_time:6.2f}s", style="bold green")

        stderr_console.print()
        stderr_console.print(table)

    def print_compilation_summary(
        self,
        output_file: Path,
        total_time: float,
        theme_name: str,
        pack: Optional[KnowledgePack],
        diagrams_count: int,
        is_pdf: bool,
        is_crate: bool
    ) -> None:
        """Renders an executive compilation dashboard card to stderr_console."""
        if self.config.quiet:
            return

        file_size_str = "N/A"
        sha256_short = ""
        if output_file.is_file():
            try:
                sz = float(output_file.stat().st_size)
                for unit in ['B', 'KB', 'MB', 'GB']:
                    if sz < 1024.0:
                        file_size_str = f"{sz:.1f} {unit}" if unit != 'B' else f"{int(sz)} B"
                        break
                    sz /= 1024.0
                import hashlib
                hasher = hashlib.sha256()
                with open(output_file, "rb") as f:
                    while chunk := f.read(65536):
                        hasher.update(chunk)
                full_digest = hasher.hexdigest()
                sha256_short = f"{full_digest[:12]}…{full_digest[-12:]}"
            except Exception:
                pass

        if is_crate:
            format_badge = "[bold yellow]RO-Crate v1.1 Package (.crate.zip)[/bold yellow]"
        elif is_pdf:
            format_badge = "[bold red]Print PDF Document (.pdf)[/bold red]"
        else:
            format_badge = "[bold cyan]Self-Contained HTML Report (.html)[/bold cyan]"

        grid = Table.grid(padding=(0, 2))
        grid.add_column(style="bold yellow", justify="right")
        grid.add_column()

        grid.add_row("Output Target:", f"[bold white]{output_file.name}[/bold white]")
        grid.add_row("Format:", format_badge)
        grid.add_row("File Size:", f"[bold white]{file_size_str}[/bold white]")
        grid.add_row("Theme Style:", f"[bold cyan]{theme_name}[/bold cyan]")

        if pack and pack.entities:
            by_type = {}
            for e in pack.entities.values():
                by_type[e.type] = by_type.get(e.type, 0) + 1
            top_types = ", ".join(f"{k.upper()}: {v}" for k, v in sorted(by_type.items(), key=lambda x: -x[1])[:4])
            grid.add_row("Knowledge Pack:", f"[bold green]{len(pack.entities)} entities[/bold green] [dim]({top_types})[/dim]")

        if diagrams_count > 0:
            grid.add_row("Diagrams:", f"[bold magenta]{diagrams_count} rendered[/bold magenta]")

        grid.add_row("Compilation Time:", f"[bold green]{total_time:.2f}s[/bold green]")
        if sha256_short:
            grid.add_row("SHA-256 Digest:", f"[dim]{sha256_short}[/dim]")

        panel = Panel(
            grid,
            title="[bold green]■ Compilation Summary[/bold green]",
            subtitle=f"[dim]{output_file.resolve()}[/dim]",
            box=box.ROUNDED,
            border_style="green"
        )
        stderr_console.print()
        stderr_console.print(panel)

    # Backwards-compatibility proxies for tests
    def _compile_pdf(self, src_html: Path, dst_pdf: Path, **kwargs):
        return Stage5Export.compile_pdf(src_html, dst_pdf, **kwargs)

    def _should_build_dossier_header(self, style: str, frontmatter: Optional[Dict[str, Any]]) -> bool:
        return Stage4Compilation.should_build_dossier_header(style, frontmatter)

    def _build_dossier_header(self, frontmatter, title, catalog, **kwargs) -> str:
        return Stage4Compilation.build_dossier_header(frontmatter, title, catalog, **kwargs)

    @staticmethod
    def _normalize_nested_containers(content: str) -> str:
        return Stage1Ingestion.normalize_nested_containers(content)
