"""
core/theme_tool.py
Theme & Style Inspector, Linter, and Scaffolder for md-style.
Provides comprehensive diagnostic inspection, static audit rules,
and turnkey starter scaffolding for theme authors.
"""

import os
import re
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional, Any, Tuple, Set

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from core.config import STYLES_DIR
from core.diagnostics import stdout_console, stderr_console
from core.themes import ThemeResolver, ThemeDefinition, ResolvedTheme, STYLE_NAME_ALIASES

KNOWN_FEATURES: Set[str] = {
    "interactive_viewer",
    "callouts",
    "sticky_tables",
    "break_ranges",
    "entity_inspector",
    "dark_hud",
    "table_nowrap",
    "legal_inspector",
    "ballot_print",
    "auto_toc",
    "toc",
}

KNOWN_PAPER_SIZES: Set[str] = {
    "a4", "a3", "a5", "letter", "legal", "ledger", "tabloid"
}

VALID_MARGIN_UNIT_RE = re.compile(r"^\s*([0-9]+(?:\.[0-9]+)?)\s*(mm|cm|in|pt|px)\s*$", re.IGNORECASE)

KNOWN_PAGED_TOKENS: Set[str] = {
    "doc_title",
    "title",
    "date",
    "classification",
    "page_counter",
    "total_pages",
    "page",
    "fingerprint",
    "fingerprint_short",
    "author",
    "heading",
}


@dataclass
class LintMessage:
    rule_id: str
    severity: str  # "ERROR", "WARNING", "INFO"
    message: str
    theme_name: str
    file_path: Optional[Path] = None
    line_no: Optional[int] = None


class ThemeLinter:
    """Audits theme manifests, stylesheets, Paged.js geometry, and CSS contracts."""

    def __init__(self, styles_root: Path = STYLES_DIR):
        self.styles_root = styles_root
        self.resolver = ThemeResolver(styles_root)

    def lint_all(self) -> List[LintMessage]:
        """Lints all discovered themes in styles_root."""
        messages: List[LintMessage] = []
        yaml_files = sorted(self.styles_root.glob("**/theme.yaml"))
        for yf in yaml_files:
            messages.extend(self.lint_theme_file(yf))
        return messages

    def lint_theme_name(self, theme_name: str) -> List[LintMessage]:
        """Lints a specific theme by name or path."""
        t_def = self.resolver.get_theme_definition(theme_name)
        if t_def:
            yaml_path = t_def.directory / "theme.yaml"
            if yaml_path.is_file():
                return self.lint_theme_file(yaml_path)

        # Check direct path
        cand_path = Path(theme_name)
        if cand_path.is_file() and cand_path.name == "theme.yaml":
            return self.lint_theme_file(cand_path)
        if cand_path.is_dir() and (cand_path / "theme.yaml").is_file():
            return self.lint_theme_file(cand_path / "theme.yaml")

        styles_sub = self.styles_root / theme_name / "theme.yaml"
        if styles_sub.is_file():
            return self.lint_theme_file(styles_sub)

        return [
            LintMessage(
                rule_id="manifest/not-found",
                severity="ERROR",
                message=f"Theme manifest not found for '{theme_name}'",
                theme_name=theme_name
            )
        ]

    def lint_theme_file(self, yaml_path: Path) -> List[LintMessage]:
        """Runs full audit suite on a single theme.yaml and its assets."""
        messages: List[LintMessage] = []
        rel_dir = yaml_path.parent.relative_to(self.styles_root) if yaml_path.is_relative_to(self.styles_root) else yaml_path.parent
        theme_ident = str(rel_dir).replace("\\", "/")

        # -------------------------------------------------------------
        # 1. Manifest Syntax & Structure
        # -------------------------------------------------------------
        try:
            with open(yaml_path, "r", encoding="utf-8") as f:
                raw_yaml = f.read()
            data = yaml.safe_load(raw_yaml)
        except Exception as e:
            messages.append(
                LintMessage(
                    rule_id="manifest/yaml-syntax",
                    severity="ERROR",
                    message=f"YAML parsing failed: {e}",
                    theme_name=theme_ident,
                    file_path=yaml_path
                )
            )
            return messages

        if not isinstance(data, dict):
            messages.append(
                LintMessage(
                    rule_id="manifest/yaml-syntax",
                    severity="ERROR",
                    message="Theme manifest must be a top-level mapping/dictionary",
                    theme_name=theme_ident,
                    file_path=yaml_path
                )
            )
            return messages

        # Check required fields
        name = data.get("name")
        if not name or not isinstance(name, str) or not name.strip():
            messages.append(
                LintMessage(
                    rule_id="manifest/required-fields",
                    severity="ERROR",
                    message="Missing required field 'name' in theme manifest",
                    theme_name=theme_ident,
                    file_path=yaml_path
                )
            )
        else:
            theme_ident = name.strip()
            # Naming convention
            if not re.match(r"^[a-z0-9\-_/]+$", theme_ident):
                messages.append(
                    LintMessage(
                        rule_id="manifest/naming-convention",
                        severity="WARNING",
                        message=f"Theme name '{theme_ident}' should use lowercase alphanumeric, dashes, and slashes",
                        theme_name=theme_ident,
                        file_path=yaml_path
                    )
                )

        title = data.get("title")
        if not title or not isinstance(title, str) or not title.strip():
            messages.append(
                LintMessage(
                    rule_id="manifest/required-fields",
                    severity="ERROR",
                    message="Missing or empty required field 'title' in theme manifest",
                    theme_name=theme_ident,
                    file_path=yaml_path
                )
            )

        # Inheritance check
        extends = data.get("extends")
        if extends:
            canon_extends = self.resolver.canonicalize_name(str(extends))
            if canon_extends == theme_ident:
                messages.append(
                    LintMessage(
                        rule_id="manifest/inheritance",
                        severity="ERROR",
                        message=f"Theme cannot extend itself ('{extends}')",
                        theme_name=theme_ident,
                        file_path=yaml_path
                    )
                )
            elif canon_extends not in self.resolver._themes:
                # Check if it exists on disk
                target_dir = self.styles_root / canon_extends
                if not (target_dir / "theme.yaml").exists():
                    messages.append(
                        LintMessage(
                            rule_id="manifest/inheritance",
                            severity="ERROR",
                            message=f"Base theme '{extends}' referenced by 'extends' does not exist",
                            theme_name=theme_ident,
                            file_path=yaml_path
                        )
                    )

        # -------------------------------------------------------------
        # 2. Stylesheet & Asset Existence
        # -------------------------------------------------------------
        stylesheets = data.get("stylesheets")
        if stylesheets is None:
            messages.append(
                LintMessage(
                    rule_id="assets/stylesheets-declared",
                    severity="WARNING",
                    message="Field 'stylesheets' is omitted or null",
                    theme_name=theme_ident,
                    file_path=yaml_path
                )
            )
        elif not isinstance(stylesheets, list):
            messages.append(
                LintMessage(
                    rule_id="assets/stylesheets-type",
                    severity="ERROR",
                    message="'stylesheets' must be a list of file paths",
                    theme_name=theme_ident,
                    file_path=yaml_path
                )
            )
        else:
            if not stylesheets:
                messages.append(
                    LintMessage(
                        rule_id="assets/stylesheets-empty-list",
                        severity="WARNING",
                        message="'stylesheets' list is empty; this theme adds no CSS",
                        theme_name=theme_ident,
                        file_path=yaml_path
                    )
                )
            combined_css_list: List[str] = []
            for s_item in stylesheets:
                if not isinstance(s_item, str) or not s_item.strip():
                    messages.append(
                        LintMessage(
                            rule_id="assets/stylesheet-path",
                            severity="ERROR",
                            message=f"Invalid stylesheet entry: {s_item}",
                            theme_name=theme_ident,
                            file_path=yaml_path
                        )
                    )
                    continue

                s_path = (yaml_path.parent / s_item).resolve()
                if not s_path.is_file():
                    messages.append(
                        LintMessage(
                            rule_id="assets/stylesheet-exists",
                            severity="ERROR",
                            message=f"Referenced stylesheet does not exist: '{s_item}'",
                            theme_name=theme_ident,
                            file_path=yaml_path
                        )
                    )
                else:
                    try:
                        file_size = s_path.stat().st_size
                        if file_size == 0:
                            messages.append(
                                LintMessage(
                                    rule_id="assets/non-empty",
                                    severity="WARNING",
                                    message=f"Stylesheet '{s_item}' is 0 bytes (empty file)",
                                    theme_name=theme_ident,
                                    file_path=s_path
                                )
                            )
                        else:
                            # -------------------------------------------------
                            # 3. CSS Content Rules (Brace balance, print safety)
                            # -------------------------------------------------
                            css_content = s_path.read_text(encoding="utf-8")
                            combined_css_list.append(css_content)
                            self._lint_css_content(css_content, s_path, theme_ident, data, messages)
                    except Exception as e:
                        messages.append(
                            LintMessage(
                                rule_id="assets/read-error",
                                severity="ERROR",
                                message=f"Failed to read stylesheet '{s_item}': {e}",
                                theme_name=theme_ident,
                                file_path=s_path
                            )
                        )

        # Check theme-level print-color-adjust for dark themes
        is_dark = (
            data.get("features", {}).get("dark_hud") is True
            or "dark" in theme_ident.lower()
            or "cyber" in theme_ident.lower()
        )
        if is_dark:
            combined_all = "\n".join(combined_css_list)
            has_color_adjust = (
                "print-color-adjust" in combined_all
                or "-webkit-print-color-adjust" in combined_all
            )
            # If not in local CSS, also check if it extends a base theme that defines it
            if not has_color_adjust and not data.get("extends"):
                messages.append(
                    LintMessage(
                        rule_id="css/print-color-adjust",
                        severity="WARNING",
                        message="Dark theme should include 'print-color-adjust: exact' to avoid paper bleaching on PDF export.",
                        theme_name=theme_ident,
                        file_path=yaml_path
                    )
                )

        # -------------------------------------------------------------
        # 4. Features Validation
        # -------------------------------------------------------------
        features = data.get("features")
        if features and isinstance(features, dict):
            for fk in features.keys():
                if fk not in KNOWN_FEATURES:
                    messages.append(
                        LintMessage(
                            rule_id="features/valid-keys",
                            severity="WARNING",
                            message=f"Unknown feature flag '{fk}'. Known flags: {', '.join(sorted(KNOWN_FEATURES))}",
                            theme_name=theme_ident,
                            file_path=yaml_path
                        )
                    )

        # -------------------------------------------------------------
        # 5. Paged.js Print Geometry
        # -------------------------------------------------------------
        paged_cfg = data.get("paged")
        if paged_cfg and isinstance(paged_cfg, dict):
            self._lint_paged_config(paged_cfg, yaml_path, theme_ident, messages)

        return messages

    def _lint_css_content(
        self,
        css_content: str,
        css_path: Path,
        theme_ident: str,
        theme_data: dict,
        messages: List[LintMessage]
    ) -> None:
        """Audits CSS content for syntax balance, hardcoded page sizes, and print safety."""
        # Check comment closures
        open_comments = css_content.count("/*")
        close_comments = css_content.count("*/")
        if open_comments != close_comments:
            messages.append(
                LintMessage(
                    rule_id="css/comment-balance",
                    severity="ERROR",
                    message=f"Unbalanced CSS comment blocks ({open_comments} open '/*', {close_comments} close '*/')",
                    theme_name=theme_ident,
                    file_path=css_path
                )
            )

        # Strip comments for brace checking
        stripped_css = re.sub(r"/\*.*?\*/", "", css_content, flags=re.DOTALL)
        open_braces = stripped_css.count("{")
        close_braces = stripped_css.count("}")
        if open_braces != close_braces:
            messages.append(
                LintMessage(
                    rule_id="css/brace-balance",
                    severity="ERROR",
                    message=f"Unbalanced braces in CSS ({open_braces} '{{', {close_braces} '}}')",
                    theme_name=theme_ident,
                    file_path=css_path
                )
            )

        # Hardcoded @page size conflict
        if re.search(r"@page\s*\{[^}]*\bsize\s*:[^}]+}", stripped_css, re.IGNORECASE):
            messages.append(
                LintMessage(
                    rule_id="css/hardcoded-page-size",
                    severity="WARNING",
                    message="Hardcoded '@page { size: ... }' found in CSS. Prefer declarative 'paged.size' in theme.yaml.",
                    theme_name=theme_ident,
                    file_path=css_path
                )
            )

    def _lint_paged_config(
        self,
        paged_cfg: dict,
        yaml_path: Path,
        theme_ident: str,
        messages: List[LintMessage]
    ) -> None:
        """Audits Paged.js paper geometry, margins, and template interpolation."""
        # 1. Paper size
        size = paged_cfg.get("size")
        if size and isinstance(size, str):
            clean_size = size.strip().lower()
            if clean_size not in KNOWN_PAPER_SIZES:
                messages.append(
                    LintMessage(
                        rule_id="paged/paper-size",
                        severity="WARNING",
                        message=f"Non-standard paper size '{size}'. Known standard sizes: {', '.join(sorted(KNOWN_PAPER_SIZES))}",
                        theme_name=theme_ident,
                        file_path=yaml_path
                    )
                )

        # 2. Orientation
        orientation = paged_cfg.get("orientation")
        if orientation and isinstance(orientation, str):
            if orientation.strip().lower() not in {"portrait", "landscape"}:
                messages.append(
                    LintMessage(
                        rule_id="paged/orientation",
                        severity="ERROR",
                        message=f"Invalid orientation '{orientation}'. Must be 'portrait' or 'landscape'.",
                        theme_name=theme_ident,
                        file_path=yaml_path
                    )
                )

        # 3. Margins
        margins = paged_cfg.get("margins")
        if margins and isinstance(margins, dict):
            for side in ["top", "right", "bottom", "left"]:
                val = margins.get(side)
                if val:
                    val_str = str(val).strip()
                    m_match = VALID_MARGIN_UNIT_RE.match(val_str)
                    if not m_match:
                        messages.append(
                            LintMessage(
                                rule_id="paged/margins-format",
                                severity="ERROR",
                                message=f"Margin '{side}: {val}' has invalid unit. Must use mm, cm, in, pt, or px.",
                                theme_name=theme_ident,
                                file_path=yaml_path
                            )
                        )
                    else:
                        num = float(m_match.group(1))
                        unit = m_match.group(2).lower()
                        # Convert approx to mm for bounds check
                        mm_val = num * 10.0 if unit == "cm" else (num * 25.4 if unit == "in" else (num * 0.352778 if unit == "pt" else num))
                        if unit != "px":
                            if mm_val < 5.0:
                                messages.append(
                                    LintMessage(
                                        rule_id="paged/margins-bounds",
                                        severity="WARNING",
                                        message=f"Margin '{side}: {val}' is under 5mm and risks hardware printer clipping.",
                                        theme_name=theme_ident,
                                        file_path=yaml_path
                                    )
                                )
                            elif mm_val > 55.0:
                                messages.append(
                                    LintMessage(
                                        rule_id="paged/margins-bounds",
                                        severity="WARNING",
                                        message=f"Margin '{side}: {val}' exceeds 55mm and may excessively squeeze content.",
                                        theme_name=theme_ident,
                                        file_path=yaml_path
                                    )
                                )

        # 4. Header & Footer Template Tokens
        for section in ["headers", "footers"]:
            slots = paged_cfg.get(section)
            if slots and isinstance(slots, dict):
                for pos, tmpl in slots.items():
                    if not isinstance(tmpl, str):
                        continue
                    # Check brace balance
                    if tmpl.count("{") != tmpl.count("}"):
                        messages.append(
                            LintMessage(
                                rule_id="paged/template-syntax",
                                severity="ERROR",
                                message=f"Unbalanced braces in {section}.{pos}: '{tmpl}'",
                                theme_name=theme_ident,
                                file_path=yaml_path
                            )
                        )
                        continue

                    # Extract placeholder tokens
                    tokens = re.findall(r"\{([^}]+)\}", tmpl)
                    for tok in tokens:
                        raw_tok = tok.strip()
                        expr = raw_tok.split("|", 1)[0].strip() if "|" in raw_tok else raw_tok
                        if expr.startswith("i18n."):
                            # Verify i18n namespace
                            ns = expr[5:].split(".")[0]
                            # Check if catalog exists
                            cat_dir = self.styles_root / "i18n" / ns
                            cat_file = self.styles_root / "i18n" / f"{ns}.json"
                            theme_cat_dir = yaml_path.parent / "i18n"
                            if not (cat_dir.is_dir() or cat_file.is_file() or theme_cat_dir.is_dir() or (self.styles_root / "i18n").is_dir()):
                                messages.append(
                                    LintMessage(
                                        rule_id="i18n/catalog-exists",
                                        severity="WARNING",
                                        message=f"Template token '{tok}' uses i18n namespace '{ns}', but no corresponding catalog was found.",
                                        theme_name=theme_ident,
                                        file_path=yaml_path
                                    )
                                )
                        elif expr not in KNOWN_PAGED_TOKENS and not expr.startswith(("meta.", "string(", "counter(")):
                            messages.append(
                                LintMessage(
                                    rule_id="paged/template-syntax",
                                    severity="INFO",
                                    message=f"Template token '{{{expr}}}' in {section}.{pos} will rely on dynamic document frontmatter.",
                                    theme_name=theme_ident,
                                    file_path=yaml_path
                                )
                            )

        # 5. First page booleans
        first_page = paged_cfg.get("first_page")
        if first_page and isinstance(first_page, dict):
            for k in ["show_header", "show_footer"]:
                if k in first_page and not isinstance(first_page[k], bool):
                    messages.append(
                        LintMessage(
                            rule_id="paged/first-page-booleans",
                            severity="ERROR",
                            message=f"first_page.{k} must be a boolean (true/false), got: {first_page[k]!r}",
                            theme_name=theme_ident,
                            file_path=yaml_path
                        )
                    )


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


class ThemeScaffolder:
    """Generates starter template boilerplate for new custom themes."""

    def __init__(self, styles_root: Path = STYLES_DIR):
        self.styles_root = styles_root

    def scaffold(self, target_name: str, extends: str = "base", output_root: Optional[Path] = None) -> Path:
        """Scaffolds a new theme folder with theme.yaml and custom CSS."""
        clean_name = target_name.strip().strip("/").lower()
        if not re.match(r"^[a-z0-9\-_/]+$", clean_name):
            raise ValueError(f"Theme name '{clean_name}' contains invalid characters.")

        root = output_root or self.styles_root
        target_dir = root / clean_name
        target_dir.mkdir(parents=True, exist_ok=True)

        basename = target_dir.name
        css_filename = f"{basename}.css"
        yaml_path = target_dir / "theme.yaml"
        css_path = target_dir / css_filename

        title_words = [w.capitalize() for w in basename.replace("-", " ").replace("_", " ").split()]
        display_title = " ".join(title_words) + " Theme"

        yaml_content = f"""# ==============================================================================
# md-style Theme Definition: {clean_name}
# ==============================================================================
name: {clean_name}
title: "{display_title}"
extends: {extends}

# Cascading stylesheets injected for this theme (relative to this directory)
stylesheets:
  - {css_filename}

# Feature toggles
features:
  interactive_viewer: true
  sticky_tables: true
  break_ranges: true
  callouts: true

# Declarative CSS custom properties
variables:
  --bg-primary: "#ffffff"
  --text-main: "#1e293b"
  --accent: "#3b82f6"
  --page-header-border: "1px solid #cbd5e1"
  --page-footer-border: "1px solid #e2e8f0"

# Paged.js page geometry & print configuration
paged:
  size: A4
  orientation: portrait
  margins:
    top: 22mm
    right: 18mm
    bottom: 22mm
    left: 18mm
  headers:
    left: "{{doc_title}}"
    center: ""
    right: "string(heading)"
  footers:
    left: "{{date}}"
    center: ""
    right: "{{page_counter}}"
  first_page:
    show_header: false
    show_footer: true
"""

        css_content = f"""/* ==============================================================================
 * md-style Theme: {clean_name}
 * ============================================================================== */

/* Page & Typography Defaults */
body {{
  color: var(--text-main, #1e293b);
  background-color: var(--bg-primary, #ffffff);
}}

/* Headings */
h1, h2, h3, h4, h5, h6 {{
  color: var(--text-main, #0f172a);
}}

h1 {{
  border-bottom: 2px solid var(--accent, #3b82f6);
  padding-bottom: 0.3em;
}}

/* Tables */
table {{
  width: 100%;
  border-collapse: collapse;
  margin: 1.5em 0;
}}

th, td {{
  padding: 8px 12px;
  border: 1px solid #e2e8f0;
}}

th {{
  background-color: #f8fafc;
  font-weight: 600;
}}

/* Callouts / Blockquotes */
blockquote {{
  border-left: 4px solid var(--accent, #3b82f6);
  background-color: #f8fafc;
  padding: 0.8em 1.2em;
  margin: 1em 0;
}}
"""

        if not yaml_path.exists():
            yaml_path.write_text(yaml_content, encoding="utf-8")
        if not css_path.exists():
            css_path.write_text(css_content, encoding="utf-8")

        return target_dir


def print_lint_report(messages: List[LintMessage], console: Optional[Console] = None) -> bool:
    """Renders a styled Rich lint report. Returns True if all passed (no errors)."""
    con = console or stdout_console
    errors = [m for m in messages if m.severity == "ERROR"]
    warnings = [m for m in messages if m.severity == "WARNING"]
    infos = [m for m in messages if m.severity == "INFO"]

    if not messages:
        con.print("\n[bold green]✓ All theme manifests, stylesheets, and print rules passed audit with 0 issues![/bold green]\n")
        return True

    table = Table(
        title=f"Theme Audit & Lint Report ({len(errors)} errors, {len(warnings)} warnings, {len(infos)} info)",
        box=box.ROUNDED,
        header_style="bold magenta",
        title_justify="left"
    )
    table.add_column("Severity", justify="center", no_wrap=True)
    table.add_column("Rule ID", style="bold cyan", no_wrap=True)
    table.add_column("Theme", style="yellow", no_wrap=True)
    table.add_column("Message", style="white")

    for m in messages:
        if m.severity == "ERROR":
            sev = "[bold white on red] ERROR [/bold white on red]"
        elif m.severity == "WARNING":
            sev = "[bold black on yellow] WARN [/bold black on yellow]"
        else:
            sev = "[bold white on blue] INFO [/bold white on blue]"

        table.add_row(sev, m.rule_id, m.theme_name, m.message)

    con.print()
    con.print(table)

    if errors:
        con.print(f"[bold red]✗ Theme audit failed with {len(errors)} error(s).[/bold red]\n")
        return False
    else:
        con.print(f"[bold yellow]! Theme audit passed with {len(warnings)} warning(s).[/bold yellow]\n")
        return True
