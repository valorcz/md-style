"""
core/lint/__init__.py
Public interface for the md-style prose, rhythm, and typography linter.
"""

from core.lint.models import Issue, LintResult, LinterProfile, LintConfig
from core.lint.profiles import BUILTIN_PROFILES, DEFAULT_ALLOWED_CAPITALIZED_TERMS
from core.lint.linter import ProseLinter
from core.lint.reporter import print_lint_report
from core.lint.readability import calculate_readability, ReadabilityMetrics, count_syllables_english, count_syllables_czech

__all__ = [
    "Issue",
    "LintResult",
    "LinterProfile",
    "LintConfig",
    "BUILTIN_PROFILES",
    "DEFAULT_ALLOWED_CAPITALIZED_TERMS",
    "ProseLinter",
    "print_lint_report",
    "calculate_readability",
    "ReadabilityMetrics",
    "count_syllables_english",
    "count_syllables_czech",
]
