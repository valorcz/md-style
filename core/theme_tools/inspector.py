"""
core/theme_tools/inspector.py
Detailed inspection dashboards and cascade resolution for themes.
"""

from pathlib import Path
from typing import Optional

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.config import STYLES_DIR
from core.diagnostics import stdout_console
from core.themes import ThemeResolver


class ThemeInspector:
    """Provides detailed inspection dashboards and cascade resolution for themes."""

    def __init__(self, styles_root: Path = STYLES_DIR):
        self.styles_root = styles_root
        self.resolver = ThemeResolver(styles_root)

    def list_themes(self, console: Optional[Console] = None) -> None:
        """Renders an executive summary table of all discovered themes."""
        con = console or stdout_console
        definitions = self.resolver.list_all_theme_definitions()

        table = Table(
            title="Available md-style Themes & Print Styles",
            box=box.ROUNDED,
            header_style="bold magenta",
            title_justify="left"
        )
        table.add_column("Theme Identifier", style="bold green", no_wrap=True)
        table.add_column("Extends", style="cyan", no_wrap=True)
        table.add_column("Title / Description", style="white")
        table.add_column("CSS Files", justify="center", style="yellow", no_wrap=True)
        table.add_column("Features", justify="center", style="blue", no_wrap=True)
        table.add_column("Page", justify="center", style="dim", no_wrap=True)

        for name in sorted(definitions.keys()):
            t = definitions[name]
            extends = t.extends or "[dim]—[/dim]"
            css_count = str(len(t.stylesheets))
            features_count = str(len(t.features))
            page_info = t.paged.get("size", "A4") if t.paged else "A4"
            table.add_row(name, extends, t.title, css_count, features_count, page_info)

        con.print()
        con.print(table)
        con.print("[dim]Use [bold]md-style --theme-inspect <name>[/bold] for deep cascade diagnostics.[/dim]\n")

    def inspect_theme(self, theme_name: str, console: Optional[Console] = None) -> None:
        """Renders an in-depth diagnostic dashboard for a specific theme."""
        con = console or stdout_console
        t_def = self.resolver.get_theme_definition(theme_name)
        if not t_def:
            con.print(f"\n[bold red][ERROR][/bold red] Theme '[yellow]{theme_name}[/yellow]' not found.\n")
            return

        resolved = self.resolver.resolve(theme_name)

        # 1. Header & Inheritance Panel
        chain_str = " ➔ ".join(
            f"[bold green]{c}[/bold green]" if c == resolved.name else f"[cyan]{c}[/cyan]"
            for c in resolved.inheritance_chain
        )
        meta_grid = Table.grid(padding=(0, 2))
        meta_grid.add_column(style="bold cyan")
        meta_grid.add_column()
        meta_grid.add_row("Canonical Name:", f"[bold white]{resolved.name}[/bold white]")
        meta_grid.add_row("Display Title:", resolved.title)
        meta_grid.add_row("Directory Path:", str(t_def.directory))
        meta_grid.add_row("Inheritance Cascade:", chain_str)
        meta_grid.add_row("Syntax Highlight:", resolved.highlight_style)

        con.print()
        con.print(Panel(meta_grid, title=f"Theme Dossier — [bold magenta]{resolved.name}[/bold magenta]", box=box.ROUNDED))

        # 2. Stylesheet Cascade Table
        sheet_table = Table(title="Cascading Stylesheet Order (Injected Top to Bottom)", box=box.ROUNDED, header_style="bold yellow")
        sheet_table.add_column("#", justify="right", style="dim", width=3)
        sheet_table.add_column("Stylesheet", style="bold white")
        sheet_table.add_column("Relative Location", style="cyan")
        sheet_table.add_column("File Size", justify="right", style="green")
        sheet_table.add_column("Line Count", justify="right", style="yellow")
        sheet_table.add_column("Status", justify="center")

        for idx, s_path in enumerate(resolved.stylesheet_paths, 1):
            if s_path.is_file():
                size_kb = f"{s_path.stat().st_size / 1024:.1f} KB"
                try:
                    lines = str(sum(1 for _ in open(s_path, "r", encoding="utf-8", errors="ignore")))
                except Exception:
                    lines = "?"
                status = "[bold green]OK[/bold green]"
            else:
                size_kb = "—"
                lines = "—"
                status = "[bold red]MISSING[/bold red]"

            try:
                rel = str(s_path.relative_to(self.styles_root))
            except ValueError:
                rel = s_path.name

            sheet_table.add_row(str(idx), s_path.name, rel, size_kb, lines, status)

        con.print(sheet_table)

        # 3. Features & Capabilities
        feat_table = Table(title="Feature Flags & Capabilities", box=box.ROUNDED, header_style="bold blue")
        feat_table.add_column("Feature Flag", style="bold white")
        feat_table.add_column("State", justify="center")
        feat_table.add_column("Inherited From", style="cyan")

        for fk, fv in sorted(resolved.features.items()):
            state = "[bold green]ENABLED[/bold green]" if fv else "[dim red]DISABLED[/dim red]"
            source = resolved.feature_sources.get(fk, "—")
            feat_table.add_row(fk, state, source)

        con.print(feat_table)

        # 4. CSS Custom Properties
        var_table = Table(title=f"Resolved CSS Custom Properties ({len(resolved.variables)} active)", box=box.ROUNDED, header_style="bold magenta")
        var_table.add_column("Property", style="bold cyan")
        var_table.add_column("Value", style="white")
        var_table.add_column("Source Theme", style="yellow")

        for vk, vv in sorted(resolved.variables.items()):
            var_name = vk if vk.startswith("--") else f"--{vk}"
            source = resolved.variable_sources.get(vk, "—")
            var_table.add_row(var_name, vv, source)

        con.print(var_table)

        # 5. Paged.js Print Specification
        paged_cfg = resolved.paged
        if paged_cfg:
            paged_grid = Table.grid(padding=(0, 2))
            paged_grid.add_column(style="bold yellow")
            paged_grid.add_column()

            margins = paged_cfg.get("margins", {})
            margin_str = f"Top: {margins.get('top', '22mm')}, Right: {margins.get('right', '18mm')}, Bottom: {margins.get('bottom', '22mm')}, Left: {margins.get('left', '18mm')}"
            paged_grid.add_row("Page Format:", f"{paged_cfg.get('size', 'A4')} ({paged_cfg.get('orientation', 'portrait')})")
            paged_grid.add_row("Margins:", margin_str)

            headers = paged_cfg.get("headers", {})
            h_str = f"L: '{headers.get('left', '')}'  |  C: '{headers.get('center', '')}'  |  R: '{headers.get('right', '')}'"
            paged_grid.add_row("Running Headers:", h_str)

            footers = paged_cfg.get("footers", {})
            f_str = f"L: '{footers.get('left', '')}'  |  C: '{footers.get('center', '')}'  |  R: '{footers.get('right', '')}'"
            paged_grid.add_row("Running Footers:", f_str)

            first_page = paged_cfg.get("first_page", {})
            fp_str = f"Header: {'Yes' if first_page.get('show_header', False) else 'No'}  |  Footer: {'Yes' if first_page.get('show_footer', True) else 'No'}"
            paged_grid.add_row("First Page:", fp_str)

            con.print(Panel(paged_grid, title="Paged.js Print & Margin Specification", box=box.ROUNDED))
        con.print()
