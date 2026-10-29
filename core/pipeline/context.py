"""
core/pipeline/context.py
Pipeline configuration and shared execution context.
"""

from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional, List, Dict, Any

from core.diagnostics import PipelineTimer, DiagnosticMetrics
from core.themes import ResolvedTheme
from core.kb.models import KnowledgePack
from core.i18n import I18nCatalog

DISALLOWED_INPUT_EXTENSIONS = {
    ".pdf", ".html", ".htm", ".xhtml", ".docx", ".doc", ".odt",
    ".epub", ".zip", ".tar", ".gz", ".png", ".jpg", ".jpeg",
    ".gif", ".webp", ".svg", ".exe", ".bin", ".wasm", ".pyc"
}

def validate_input_file(input_path: Path) -> None:
    """Validates that the input file exists and is a readable text / Markdown document."""
    if not input_path.exists():
        raise FileNotFoundError(f"Input file not found: {input_path}")
    if not input_path.is_file():
        raise ValueError(f"Input path is not a regular file: {input_path}")

    ext = input_path.suffix.lower()
    if ext in DISALLOWED_INPUT_EXTENSIONS:
        raise ValueError(
            f"Unsupported input file format '{ext}' for '{input_path.name}'. "
            f"md-style expects a Markdown or text document (.md, .markdown, .txt)."
        )

    # Inspect first 4096 bytes for binary signatures / null bytes / HTML
    try:
        with open(input_path, "rb") as f:
            chunk = f.read(4096)
    except Exception as e:
        raise ValueError(f"Cannot read input file '{input_path.name}': {e}")

    # 1. Null byte check (standard binary file detection)
    if b"\x00" in chunk:
        raise ValueError(
            f"Input file '{input_path.name}' appears to be a binary file, not a text/markdown document."
        )

    # 2. PDF magic bytes (%PDF-)
    if chunk.startswith(b"%PDF-"):
        raise ValueError(
            f"Input file '{input_path.name}' is a PDF document, not a Markdown document."
        )

    # 3. HTML document detection (if file does not have .md/.markdown extension and begins with HTML doctype/tag)
    if ext not in {".md", ".markdown", ".mdown", ".mkd"}:
        stripped = chunk.lstrip().lower()
        if stripped.startswith(b"<!doctype html") or stripped.startswith(b"<html"):
            raise ValueError(
                f"Input file '{input_path.name}' appears to be raw HTML, not a Markdown document."
            )


@dataclass
class PipelineConfig:
    input_file: Path
    output_file: Optional[Path] = None
    style: Optional[str] = None
    title: Optional[str] = None
    lang: Optional[str] = None
    toc: Optional[bool] = None
    toc_depth: int = 3
    number_sections: bool = False
    embed_resources: bool = True
    embed_source: bool = True
    highlight_style: Optional[str] = None
    paged: bool = False
    print_mode: bool = False
    generate_pdf: bool = False
    pdf_engine: Optional[str] = None
    generate_crate: bool = False
    evidence_path: Optional[Path] = None
    interactive_viewer: Optional[bool] = None
    enable_mermaid: bool = True
    auto_nowrap: bool = True
    allow_online: bool = True
    enrich: Optional[bool] = None
    kb_refresh: Optional[str] = None  # None, "incremental", "sources", "force"
    knowledge_path: Optional[Path] = None
    i18n_path: Optional[Path] = None
    toc_levels: Optional[str] = None
    font_subsets: Optional[str] = None
    all_fonts: bool = False
    embed_diagram_fonts: bool = False
    verbose: bool = False
    quiet: bool = False


@dataclass
class PipelineContext:
    config: PipelineConfig
    timer: PipelineTimer = field(default_factory=PipelineTimer)
    metrics: DiagnosticMetrics = field(default_factory=DiagnosticMetrics)

    # Stage 1 artifacts
    raw_content: str = ""
    cleaned_content: str = ""
    frontmatter: Dict[str, Any] = field(default_factory=dict)
    doc_title: str = ""
    doc_lang: str = "en"
    style_param: str = "forensic"
    catalog: Optional[I18nCatalog] = None
    is_crate: bool = False
    target_html: Optional[Path] = None
    final_output_file: Optional[Path] = None

    # Stage 2 artifacts
    pack: Optional[KnowledgePack] = None

    # Stage 3 artifacts
    resolved_theme: Optional[ResolvedTheme] = None

    # Stage 4 artifacts
    html_fragment: str = ""
    toc_html: str = ""
    toc_entries: List[Dict[str, Any]] = field(default_factory=list)
    diagram_count: int = 0

    # Stage 5 artifacts
    bundled_html: str = ""
    sha256_digest: str = ""
