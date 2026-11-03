"""
core/lint/models.py
Data structures and models for prose, rhythm, and typography linting.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Set, Any


@dataclass
class LinterProfile:
    name: str
    title: str
    description: str
    target_bold: Tuple[float, float]
    max_bold: float  # WARN threshold
    fail_bold: float  # FAIL threshold
    target_italic: Tuple[float, float]
    max_italic: float  # WARN threshold
    fail_italic: float  # FAIL threshold
    allow_bullet_bold_label: bool
    penalize_bold_stacking: bool
    max_paragraph_words: int
    min_paragraph_words: int
    max_list_items: int
    max_heading_chars: int
    max_heading_words: int


@dataclass
class LintConfig:
    profile_name: Optional[str] = None
    profiles: Dict[str, LinterProfile] = field(default_factory=dict)
    allowed_capitalized_terms: Set[str] = field(default_factory=set)
    disabled_rules: Set[str] = field(default_factory=set)
    enabled_rules: Optional[Set[str]] = None
    rule_overrides: Dict[str, Dict[str, Any]] = field(default_factory=dict)
    strict: bool = False
    verbose: bool = False
    lang: str = "en"


@dataclass
class Issue:
    code: str
    category: str
    message: str
    line: Optional[int] = None
    snippet: Optional[str] = None
    severity: str = "WARN"  # "INFO", "WARN", "FAIL"
    penalty: float = 2.0


@dataclass
class LintResult:
    file_path: Optional[Path]
    profile: LinterProfile
    detected_via: str = "default"
    total_words: int = 0
    bold_words: int = 0
    italic_words: int = 0
    bold_density: float = 0.0
    italic_density: float = 0.0
    issues: List[Issue] = field(default_factory=list)
    score: float = 100.0
    lang: str = "en"
    readability: Optional[Any] = None

    @property
    def grade(self) -> str:
        if self.score >= 95:
            return "A+"
        elif self.score >= 90:
            return "A"
        elif self.score >= 80:
            return "B"
        elif self.score >= 70:
            return "C"
        elif self.score >= 60:
            return "D"
        else:
            return "F"
