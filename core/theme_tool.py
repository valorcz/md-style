"""
core/theme_tool.py
Facade for theme inspection, linting, and scaffolding tools.
Delegates to the modular core.theme_tools package.
"""

from core.theme_tools import (
    KNOWN_FEATURES,
    KNOWN_PAPER_SIZES,
    KNOWN_PAGED_TOKENS,
    VALID_MARGIN_UNIT_RE,
    LintMessage,
    ThemeLinter,
    ThemeInspector,
    ThemeScaffolder,
    print_lint_report,
)

__all__ = [
    "KNOWN_FEATURES",
    "KNOWN_PAPER_SIZES",
    "KNOWN_PAGED_TOKENS",
    "VALID_MARGIN_UNIT_RE",
    "LintMessage",
    "ThemeLinter",
    "ThemeInspector",
    "ThemeScaffolder",
    "print_lint_report",
]
