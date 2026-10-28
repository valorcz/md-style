"""
core/parser/__init__.py
Pure-Python Markdown AST and rendering engine package.
"""

from core.parser.engine import MarkdownParser, pygments_highlight
from core.parser.transforms import (
    transform_callouts,
    transform_tables,
    transform_entities,
    transform_headings_and_extract_toc,
)

__all__ = [
    "MarkdownParser",
    "pygments_highlight",
    "transform_callouts",
    "transform_tables",
    "transform_entities",
    "transform_headings_and_extract_toc",
]
