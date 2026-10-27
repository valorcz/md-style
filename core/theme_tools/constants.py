"""
core/theme_tools/constants.py
Constants, regex rules, and message dataclasses for theme inspection and linting.
"""

import re
from pathlib import Path
from dataclasses import dataclass
from typing import Set, Optional

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
