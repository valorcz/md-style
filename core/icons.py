"""
core/icons.py
Externalized vector icon loader and cache manager.
Zero hardcoded SVGs in Python: reads discrete SVG asset files from data/icons/
or fetches & caches from official vector registries.
"""

import os
import re
import urllib.request
from pathlib import Path
from typing import Optional, Dict

from core.config import ICONS_DIR, CACHE_DIR
from core.diagnostics import Diagnostics

ICON_CACHE_DIR = CACHE_DIR / "icons"

class IconService:
    """Provides vector SVG icons loaded from disk or CDN cache."""

    def __init__(self, icons_dir: Path = ICONS_DIR, cache_dir: Path = ICON_CACHE_DIR, allow_online: bool = True):
        self.icons_dir = icons_dir
        self.cache_dir = cache_dir
        self.allow_online = allow_online
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self._memory_cache: Dict[str, str] = {}

    def get_svg(self, name: str, extra_classes: str = "callout-icon") -> str:
        """
        Retrieves SVG markup for an icon by name.
        Looks in:
          1. Memory cache
          2. data/icons/{name}.svg
          3. data/cache/icons/{name}.svg
          4. Remote Primer Octicons CDN (cached on disk)
        """
        clean_name = name.strip().lower()
        if clean_name in self._memory_cache:
            return self._format_svg(self._memory_cache[clean_name], extra_classes)

        # 1. Local disk asset
        local_path = self.icons_dir / f"{clean_name}.svg"
        if local_path.is_file():
            try:
                svg_content = local_path.read_text(encoding="utf-8")
                self._memory_cache[clean_name] = svg_content
                return self._format_svg(svg_content, extra_classes)
            except Exception as e:
                Diagnostics.warn(f"Failed to read icon {local_path}: {e}")

        # 2. Local cache
        cache_path = self.cache_dir / f"{clean_name}.svg"
        if cache_path.is_file():
            try:
                svg_content = cache_path.read_text(encoding="utf-8")
                self._memory_cache[clean_name] = svg_content
                return self._format_svg(svg_content, extra_classes)
            except Exception:
                pass

        # 3. Remote fallback from GitHub Primer Octicons
        if self.allow_online:
            remote_url = f"https://raw.githubusercontent.com/primer/octicons/main/icons/{clean_name}-16.svg"
            try:
                req = urllib.request.Request(
                    remote_url,
                    headers={"User-Agent": "Antigravity-Tooling/2.0 (Icon Loader)"}
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    downloaded_svg = resp.read().decode("utf-8")
                if downloaded_svg and "<svg" in downloaded_svg:
                    cache_path.write_text(downloaded_svg, encoding="utf-8")
                    self._memory_cache[clean_name] = downloaded_svg
                    return self._format_svg(downloaded_svg, extra_classes)
            except Exception:
                pass

        # 4. Minimal generic fallback if completely offline and missing
        fallback = '<svg viewBox="0 0 16 16" width="16" height="16" fill="currentColor"><circle cx="8" cy="8" r="7"/></svg>'
        return self._format_svg(fallback, extra_classes)

    def _format_svg(self, svg_str: str, extra_classes: str) -> str:
        """Ensures proper class attribute and sizing on SVG tag."""
        # Replace or add class
        if 'class="' in svg_str:
            svg_str = re.sub(r'class="[^"]*"', f'class="{extra_classes}"', svg_str, count=1)
        else:
            svg_str = re.sub(r'<svg\b', f'<svg class="{extra_classes}"', svg_str, count=1)
        return svg_str
