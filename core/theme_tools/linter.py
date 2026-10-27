"""
core/theme_tools/linter.py
Static linting and audit rules for themes, stylesheets, and Paged geometry.
"""

import os
import re
import yaml
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple, Set

from rich.console import Console
from rich.table import Table
from rich import box

from core.config import STYLES_DIR
from core.diagnostics import stdout_console
from core.themes import ThemeResolver
from core.theme_tools.constants import (
    KNOWN_FEATURES,
    KNOWN_PAPER_SIZES,
    KNOWN_PAGED_TOKENS,
    VALID_MARGIN_UNIT_RE,
    LintMessage,
)

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
