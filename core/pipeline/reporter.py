"""
core/pipeline/reporter.py
Presentation reporter for terminal diagnostics, summary cards, and KB tables.
"""

from pathlib import Path
from typing import Dict, Any

from rich.table import Table
from rich.panel import Panel
from rich import box

from core.diagnostics import stderr_console, stdout_console, Colors
from core.pipeline.context import PipelineContext


class SummaryReporter:
    """Renders formatted Rich tables and summary cards for the document compilation pipeline."""

    @staticmethod
    def render_kb_inventory(context: PipelineContext) -> None:
        """Renders the Stage 2 Knowledge Pack inventory table in verbose mode."""
        pack = context.pack
        if not pack or not pack.entities:
            return

        by_type: Dict[str, Dict[str, Any]] = {}
        for e_id, e in pack.entities.items():
            t = e.type or "entity"
            if t not in by_type:
                by_type[t] = {"domain": e.domain or "general", "items": []}
            by_type[t]["items"].append(e_id)

        kb_table = Table(
            title=f"Knowledge Pack Inventory ({len(pack.entities)} entities)",
            box=box.ROUNDED,
            header_style="bold magenta",
            show_header=True
        )
        kb_table.add_column("Type", style="bold cyan", no_wrap=True)
        kb_table.add_column("Domain", style="blue", no_wrap=True)
        kb_table.add_column("Count", justify="right", style="bold yellow", no_wrap=True)
        kb_table.add_column("Sample Identifiers", style="white")

        def format_preview(val: str) -> str:
            if len(val) > 22:
                return f"{val[:8]}…{val[-6:]}"
            return val

        for t, info in sorted(by_type.items()):
            items = info["items"]
            dom = info["domain"]
            sample_limit = 3 if any(len(x) > 16 for x in items[:4]) else 4
            samples = [f"`{format_preview(x)}`" for x in items[:sample_limit]]
            sample_str = ", ".join(samples)
            if len(items) > sample_limit:
                sample_str += f" [dim](+{len(items) - sample_limit} more)[/dim]"
            kb_table.add_row(t.upper(), dom, str(len(items)), sample_str)

        stderr_console.print()
        stderr_console.print(kb_table)
        stderr_console.print()

    @staticmethod
    def render_summary_card(
        output_path: Path,
        format_name: str,
        theme_name: str,
        total_time: float,
        sha256_digest: str = "",
        context: Optional[PipelineContext] = None
    ) -> None:
        """Renders the final publication summary card using Rich."""
        try:
            file_size_bytes = output_path.stat().st_size
            if file_size_bytes < 1024 * 1024:
                file_size_str = f"{file_size_bytes / 1024:.1f} KB"
            else:
                file_size_str = f"{file_size_bytes / (1024 * 1024):.1f} MB"
        except Exception:
            file_size_str = "N/A"

        summary_table = Table(box=None, show_header=False, padding=(0, 2))
        summary_table.add_column("Property", style="bold cyan", justify="right")
        summary_table.add_column("Value", style="white")

        summary_table.add_row("Output Target:", f"[bold green]{output_path.name}[/bold green]")
        summary_table.add_row("Format:", format_name)
        summary_table.add_row("File Size:", file_size_str)
        summary_table.add_row("Theme Style:", f"[yellow]{theme_name}[/yellow]")

        if context and context.pack and context.pack.entities:
            entity_count = len(context.pack.entities)
            types: Dict[str, int] = {}
            for e in context.pack.entities.values():
                t = e.type or "entity"
                types[t] = types.get(t, 0) + 1
            types_str = ", ".join(f"{k.upper()}: {v}" for k, v in sorted(types.items()))
            summary_table.add_row("Knowledge Pack:", f"{entity_count} entities ({types_str})")

        if context and context.diagram_count > 0:
            summary_table.add_row("Diagrams:", f"{context.diagram_count} rendered")

        summary_table.add_row("Compilation Time:", f"{total_time:.2f}s")
        if sha256_digest:
            summary_table.add_row("SHA-256 Digest:", f"[dim]{sha256_digest[:12]}…{sha256_digest[-12:]}[/dim]")

        summary_panel = Panel(
            summary_table,
            title="[bold white]■ Compilation Summary[/bold white]",
            subtitle=f"[dim]{output_path}[/dim]",
            border_style="bright_blue",
            box=box.ROUNDED,
            expand=False,
            padding=(1, 2)
        )

        stdout_console.print()
        stdout_console.print(summary_panel)
