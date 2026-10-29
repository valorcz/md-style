"""
core/fonts.py
100% self-contained font inliner and offline cache manager.
Recursively resolves CSS @import declarations (including Google Fonts)
and inlines all .woff2 / .ttf font files as base64 data URIs.
"""

import os
import re
import hashlib
import base64
import urllib.request
from pathlib import Path
from typing import Optional, Dict, Set, Any

from core.config import FONTS_CACHE_DIR
from core.diagnostics import Diagnostics

BROWSER_USER_AGENT = (
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)

IMPORT_REGEX = re.compile(r'@import\s+(?:url\([\'"]?([^\'")]+)[\'"]?\)|[\'"]([^\'"]+)[\'"])\s*;?', re.IGNORECASE)
FONT_URL_REGEX = re.compile(r'url\([\'"]?(https?://[^\'")]+|\.?[^\'")\s]+\.(?:woff2|woff|ttf|otf))[\'"]?\)', re.IGNORECASE)
FONT_FACE_BLOCK_REGEX = re.compile(r'(/\*\s*([a-z0-9_-]+)\s*\*/\s*)?(@font-face\s*\{[^}]+\})', re.DOTALL | re.IGNORECASE)

DEFAULT_LATIN_SUBSETS: Set[str] = {"latin", "latin-ext"}


def resolve_font_subsets(
    lang: str = "en",
    font_subsets_opt: Optional[str] = None,
    all_fonts: bool = False,
    frontmatter_subsets: Optional[Any] = None,
) -> Optional[Set[str]]:
    """
    Resolves the set of font unicode subsets to embed.
    Returns None if all subsets should be embedded (no pruning).
    """
    if all_fonts:
        return None

    raw_setting = font_subsets_opt
    if raw_setting is None and frontmatter_subsets is not None:
        if isinstance(frontmatter_subsets, (list, tuple, set)):
            raw_setting = ",".join(str(s) for s in frontmatter_subsets)
        elif isinstance(frontmatter_subsets, str):
            raw_setting = frontmatter_subsets
        elif isinstance(frontmatter_subsets, bool) and not frontmatter_subsets:
            return None

    if raw_setting is not None:
        raw_val = raw_setting.strip().lower()
        if raw_val in ("all", "*", "full", "false", "off", "none"):
            return None
        if raw_val not in ("auto", "default", "true"):
            subsets = {s.strip().lower() for s in raw_val.split(",") if s.strip()}
            subsets.add("latin")
            return subsets

    # Default: Automatic based on document language
    l = (lang or "en").lower().split("-")[0].split("_")[0]

    # Cyrillic script languages
    if l in {"ru", "uk", "bg", "be", "sr", "mk", "kk", "ky", "tg", "mn"}:
        return {"latin", "latin-ext", "cyrillic", "cyrillic-ext"}

    # Greek
    if l == "el":
        return {"latin", "latin-ext", "greek", "greek-ext"}

    # Vietnamese
    if l == "vi":
        return {"latin", "latin-ext", "vietnamese"}

    # Latin-based languages (English, Czech, Slovak, German, etc.)
    return set(DEFAULT_LATIN_SUBSETS)


class FontBundler:
    """Expands CSS font imports and inlines binary fonts as base64 WOFF2 data URIs."""

    def __init__(
        self,
        cache_dir: Path = FONTS_CACHE_DIR,
        allow_online: bool = True,
        subsets: Optional[Set[str]] = None,
    ):
        self.cache_dir = cache_dir
        self.allow_online = allow_online
        self.subsets = subsets
        self.css_cache_dir = cache_dir / "css"
        self.file_cache_dir = cache_dir / "files"
        self.css_cache_dir.mkdir(parents=True, exist_ok=True)
        self.file_cache_dir.mkdir(parents=True, exist_ok=True)

    def _hash_url(self, url: str) -> str:
        return hashlib.sha256(url.strip().encode("utf-8")).hexdigest()[:20]

    def fetch_css_import(self, url: str) -> Optional[str]:
        """Fetches remote CSS (e.g. Google Fonts) with modern browser user agent."""
        url_hash = self._hash_url(url)
        cached_css = self.css_cache_dir / f"{url_hash}.css"
        if cached_css.is_file():
            try:
                return cached_css.read_text(encoding="utf-8")
            except Exception:
                pass

        if not self.allow_online:
            return None

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": BROWSER_USER_AGENT}
            )
            with urllib.request.urlopen(req, timeout=5) as resp:
                css_content = resp.read().decode("utf-8")
            if css_content:
                cached_css.write_text(css_content, encoding="utf-8")
                return css_content
        except Exception as e:
            Diagnostics.warn(f"Failed to fetch remote font stylesheet {url}: {e}")
        return None

    def fetch_font_binary(self, url: str) -> Optional[bytes]:
        """Fetches remote font file (WOFF2/TTF) and caches on disk."""
        url_hash = self._hash_url(url)
        ext = "woff2" if ".woff2" in url else ("woff" if ".woff" in url else "ttf")
        cached_file = self.file_cache_dir / f"{url_hash}.{ext}"

        if cached_file.is_file():
            try:
                return cached_file.read_bytes()
            except Exception:
                pass

        if not self.allow_online:
            return None

        try:
            req = urllib.request.Request(
                url,
                headers={"User-Agent": BROWSER_USER_AGENT}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                binary_data = resp.read()
            if binary_data:
                cached_file.write_bytes(binary_data)
                return binary_data
        except Exception as e:
            Diagnostics.warn(f"Failed to fetch font binary {url}: {e}")
        return None

    def inline_imports(self, css: str, base_dir: Path) -> str:
        """Recursively resolves @import declarations in CSS."""
        def _repl(match: re.Match) -> str:
            target = match.group(1) or match.group(2)
            if not target:
                return match.group(0)

            target = target.strip()
            if target.startswith("http://") or target.startswith("https://"):
                fetched = self.fetch_css_import(target)
                if fetched:
                    # Recursively resolve any nested imports
                    return self.inline_imports(fetched, base_dir)
                if not self.allow_online:
                    return f"/* Offline: skipped import {target} */"
                return f"/* Failed to import {target} */"
            else:
                # Local relative CSS file
                local_path = (base_dir / target).resolve()
                if local_path.is_file():
                    try:
                        content = local_path.read_text(encoding="utf-8")
                        return self.inline_imports(content, local_path.parent)
                    except Exception:
                        pass
                return f"/* Local import not found: {target} */"

        return IMPORT_REGEX.sub(_repl, css)

    def filter_css_subsets(self, css: str) -> str:
        """Filters @font-face blocks in CSS by allowed unicode subsets."""
        if self.subsets is None:
            return css

        def _repl(m: re.Match) -> str:
            full_comment = m.group(1) or ""
            subset_name = (m.group(2) or "").lower().strip()
            font_face = m.group(3)

            # If tagged with a subset comment, check if allowed
            if subset_name:
                if subset_name in self.subsets:
                    return f"{full_comment}{font_face}"
                return f"/* Pruned font subset: {subset_name} */"

            # Untagged @font-face: preserve by default
            return m.group(0)

        return FONT_FACE_BLOCK_REGEX.sub(_repl, css)

    def embed_fonts(self, css: str, base_dir: Path) -> str:
        """Finds all @font-face font URLs and converts them to base64 data URIs."""
        # Ensure any unpruned subsets are filtered before fetching/embedding
        filtered_css = self.filter_css_subsets(css) if self.subsets is not None else css

        def _repl(match: re.Match) -> str:
            url = match.group(1).strip()

            # Determine mime type
            if ".woff2" in url.lower():
                mime = "font/woff2"
            elif ".woff" in url.lower():
                mime = "font/woff"
            elif ".ttf" in url.lower():
                mime = "font/ttf"
            elif ".otf" in url.lower():
                mime = "font/otf"
            else:
                mime = "font/woff2"

            binary_data: Optional[bytes] = None

            if url.startswith("http://") or url.startswith("https://"):
                binary_data = self.fetch_font_binary(url)
            else:
                # Local font file
                local_font = (base_dir / url).resolve()
                if local_font.is_file():
                    try:
                        binary_data = local_font.read_bytes()
                    except Exception:
                        pass

            if binary_data:
                b64_str = base64.b64encode(binary_data).decode("ascii")
                return f'url("data:{mime};base64,{b64_str}")'

            # If remote font failed or offline, avoid leaving WAN url in output
            if url.startswith("http://") or url.startswith("https://"):
                return 'local("")'

            # If failed, leave original url
            return match.group(0)

        return FONT_URL_REGEX.sub(_repl, filtered_css)

    def process_css(self, css: str, base_dir: Path) -> str:
        """Full pipeline: inlines @imports, filters subsets, and embeds font binaries as base64."""
        expanded_css = self.inline_imports(css, base_dir)
        filtered_css = self.filter_css_subsets(expanded_css)
        embedded_css = self.embed_fonts(filtered_css, base_dir)
        return embedded_css
