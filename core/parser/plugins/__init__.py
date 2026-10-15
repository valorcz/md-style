"""
core/parser/plugins/__init__.py
Custom markdown-it-py plugins for md-style.
"""

from .pandoc_divs import pandoc_divs_plugin
from .callouts import callouts_plugin
from .toc import toc_plugin, inline_toc, render_toc_html
from .mermaid import mermaid_plugin
from .d2 import d2_plugin

__all__ = [
    "pandoc_divs_plugin",
    "callouts_plugin",
    "toc_plugin",
    "inline_toc",
    "render_toc_html",
    "mermaid_plugin",
    "d2_plugin",
]
