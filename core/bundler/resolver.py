"""
core/bundler/resolver.py
Multi-root asset path resolver and base64 encoder for document bundling.
"""

import base64
import mimetypes
from pathlib import Path
from typing import Optional, List, Tuple

from core.diagnostics import Diagnostics


class AssetResolver:
    """Resolves local document assets across multiple directory roots and provides base64 encoding."""

    def __init__(self, doc_dir: Path):
        self.doc_dir = doc_dir

    def resolve_asset_path(self, src: str) -> Tuple[Optional[Path], List[Path]]:
        """Resolves a local image/asset path using multi-root search:

        1. doc_dir / src
        2. doc_dir.parent / src
        3. cwd / src
        Returns: (resolved_path, candidate_paths_checked)
        """
        clean_src = src.split("?")[0].split("#")[0].strip()
        if Path(clean_src).is_absolute():
            p = Path(clean_src)
            return (p if p.is_file() else None, [p])

        candidates = [
            (self.doc_dir / clean_src).resolve(),
            (self.doc_dir.parent / clean_src).resolve(),
            (Path.cwd() / clean_src).resolve(),
        ]

        unique_candidates: List[Path] = []
        for c in candidates:
            if c not in unique_candidates:
                unique_candidates.append(c)

        for candidate in unique_candidates:
            if candidate.is_file():
                return candidate, unique_candidates

        return None, unique_candidates

    @staticmethod
    def encode_file_base64(file_path: Path) -> Optional[str]:
        """Reads a file and returns an RFC 2397 Data URI string."""
        if not file_path.is_file():
            return None
        try:
            mime, _ = mimetypes.guess_type(str(file_path))
            if not mime:
                mime = "application/octet-stream"
            with open(file_path, "rb") as f:
                encoded = base64.b64encode(f.read()).decode("ascii")
            return f"data:{mime};base64,{encoded}"
        except Exception as e:
            Diagnostics.warn(f"Failed to base64-encode {file_path}: {e}")
            return None
