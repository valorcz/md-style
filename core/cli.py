"""
core/cli.py
Native CLI entrypoint for md-style / md-to-report v3 (Pure Python).
"""

import sys
import os
import shutil
import subprocess
import argparse
from pathlib import Path
from typing import Optional

from core.diagnostics import Colors, Diagnostics
from core.engine import ReportEngine, PipelineConfig
from core.themes import ThemeResolver
from core.kb import KnowledgeLifecycleManager

def check_prerequisites(generate_pdf: bool = False, enable_mermaid: bool = True) -> None:
    """Verifies optional system tools for PDF export."""
    if generate_pdf:
        has_chrome = any(shutil.which(cmd) for cmd in [
            "chromium", "chromium-browser", "google-chrome",
            "google-chrome-stable", "brave", "microsoft-edge"
        ])
        if not has_chrome:
            Diagnostics.warn(
                "No Chromium-based browser was found in PATH. PDF generation might fail."
            )

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md-style",
        description="Pure-Python Markdown Report Generator with Knowledge Packs & Svelte Viewer",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run md-style report.md -s forensic/cyber -o output.html
  uv run md-style report.md --kb-refresh
  uv run md-style report.md --kb-refresh=sources
  uv run md-style report.md --kb-refresh=force
  uv run md-style report.md -s svj/invitation --pdf
  uv run md-style --list-styles
        """
    )

    parser.add_argument("input", nargs="?", default=None, help="Source Markdown document")
    parser.add_argument("output", nargs="?", default=None, help="Target HTML/PDF file")
    parser.add_argument("-o", "--output", dest="output_opt", help="Target HTML/PDF file")
    parser.add_argument("-s", "--style", help="Style name or theme (e.g. forensic/cyber, svj/invitation)")
    parser.add_argument("-t", "--title", help="Override document title")
    parser.add_argument("-l", "--lang", help="Override document language (e.g. cs, en, sk, de)")

    # TOC
    parser.add_argument("--toc", action="store_true", default=True, help="Enable Table of Contents (default: True)")
    parser.add_argument("--no-toc", dest="toc", action="store_false", help="Disable Table of Contents")
    parser.add_argument("--toc-depth", type=int, default=3, help="TOC heading depth (default: 3)")
    parser.add_argument("--toc-levels", default=None, help="Comma-separated heading levels for TOC (e.g. '2' or '2,3')")
    parser.add_argument("--i18n", dest="i18n_path", default=None, help="Path to custom i18n JSON dictionary file")
    parser.add_argument("-N", "--number-sections", action="store_true", help="Auto-number sections")

    # Layout & Output Modes
    parser.add_argument("--paged", action="store_true", help="Enable Paged.js preview mode")
    parser.add_argument("--print", dest="print_mode", action="store_true", help="Enable Native Print mode")
    parser.add_argument("-p", "--pdf", dest="generate_pdf", action="store_true", help="Generate PDF directly via Chromium")
    parser.add_argument("--highlight-style", default=None, help="Pygments syntax highlighting theme (e.g. one-dark, monokai, friendly, github-dark)")
    parser.add_argument("--embed-resources", action="store_true", default=True, help="Embed resources into self-contained HTML (default: True)")
    parser.add_argument("--no-embed-resources", dest="embed_resources", action="store_false", help="Link external stylesheets instead of inlining")
    parser.add_argument("--embed-source", action="store_true", default=True, help="Embed original Markdown source in HTML archive (default: True)")
    parser.add_argument("--no-embed-source", dest="embed_source", action="store_false", help="Do not embed Markdown source in HTML archive")
    parser.add_argument("--open", dest="open_after", action="store_true", help="Open generated report in default viewer")

    # Knowledge Pack & Refresh
    parser.add_argument(
        "--kb-refresh",
        nargs="?",
        const="incremental",
        choices=["incremental", "sources", "force"],
        default=None,
        help="Refresh Knowledge Pack entities (default: incremental)"
    )
    parser.add_argument("-k", "--knowledge", dest="knowledge_path", default=None, help="Path to custom knowledge directory or YAML/JSON file")
    parser.add_argument("--offline", dest="allow_online", action="store_false", default=True, help="Disable on-demand online scraping for indicators")
    parser.add_argument("--no-mermaid", dest="enable_mermaid", action="store_false", default=True, help="Disable Mermaid diagram rendering")
    parser.add_argument("--no-auto-nowrap", dest="auto_nowrap", action="store_false", default=True, help="Disable auto-nowrap on tables")

    # Diagnostics & Utilities
    parser.add_argument("--list-styles", action="store_true", help="List all available built-in document styles")
    parser.add_argument("--kb-status", action="store_true", help="Display Knowledge Pack entity counts and provenance")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose debug output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet output (errors only)")

    return parser

def list_available_styles() -> None:
    resolver = ThemeResolver()
    print(f"\n{Colors.BOLD}Available md-style Themes:{Colors.RESET}")
    for name, theme_def in sorted(resolver._themes.items()):
        if "/" in name or name == "base":
            chain_str = f" (extends: {theme_def.extends})" if theme_def.extends else ""
            print(f"  - {Colors.GREEN}{name}{Colors.RESET}{Colors.CYAN}{chain_str}{Colors.RESET}: {theme_def.title}")
    print()

def show_kb_status(input_path: Path) -> None:
    mgr = KnowledgeLifecycleManager(input_path)
    loaded = mgr.load_existing_pack()
    if not loaded:
        print(f"No existing Knowledge Pack found at {mgr.kb_json_path}")
        return

    pack = mgr.pack
    print(f"\n{Colors.BOLD}Knowledge Pack Status for {input_path.name}:{Colors.RESET}")
    print(f"  File: {mgr.kb_json_path}")
    print(f"  Entities: {len(pack.entities)}")
    print(f"  Generated at: {pack.generated_at}")
    print(f"  Sources Digest:")
    for src, dig in pack.sources_digest.items():
        print(f"    - {src}: {dig}")

    # Entity breakdown
    by_type = {}
    by_domain = {}
    manual_overrides = 0
    for ent in pack.entities.values():
        by_type[ent.type] = by_type.get(ent.type, 0) + 1
        by_domain[ent.domain] = by_domain.get(ent.domain, 0) + 1
        if ent.provenance and ent.provenance.manual_override:
            manual_overrides += 1

    print(f"  By Domain: {by_domain}")
    print(f"  By Type: {by_type}")
    print(f"  Manual Overrides: {manual_overrides}\n")

def main():
    parser = build_parser()
    args = parser.parse_args()

    if args.list_styles:
        list_available_styles()
        sys.exit(0)

    if not args.input:
        parser.print_help()
        sys.exit(1)

    input_path = Path(args.input)
    if not input_path.exists():
        Diagnostics.error(f"Input file not found: {input_path}")
        sys.exit(1)

    if args.kb_status:
        show_kb_status(input_path)
        sys.exit(0)

    output_target = Path(args.output_opt or args.output) if (args.output_opt or args.output) else None
    generate_pdf = args.generate_pdf
    if output_target and output_target.suffix.lower() == ".pdf":
        generate_pdf = True

    # Prerequisite verification (no pandoc!)
    check_prerequisites(generate_pdf=generate_pdf, enable_mermaid=args.enable_mermaid)

    cfg = PipelineConfig(
        input_file=input_path,
        output_file=output_target,
        style=args.style,
        title=args.title,
        lang=args.lang,
        toc=args.toc,
        toc_depth=args.toc_depth,
        number_sections=args.number_sections,
        embed_resources=args.embed_resources,
        embed_source=args.embed_source,
        highlight_style=args.highlight_style,
        paged=args.paged,
        print_mode=args.print_mode,
        generate_pdf=generate_pdf,
        enable_mermaid=args.enable_mermaid,
        auto_nowrap=args.auto_nowrap,
        allow_online=args.allow_online,
        kb_refresh=args.kb_refresh,
        knowledge_path=Path(args.knowledge_path) if args.knowledge_path else None,
        i18n_path=Path(args.i18n_path) if args.i18n_path else None,
        toc_levels=args.toc_levels,
        verbose=args.verbose,
        quiet=args.quiet
    )

    try:
        engine = ReportEngine(cfg)
        out_file = engine.run()
    except KeyboardInterrupt:
        print("\nAborted by user.", file=sys.stderr)
        sys.exit(130)
    except Exception as e:
        if args.verbose:
            import traceback
            traceback.print_exc()
        else:
            Diagnostics.error(f"Compilation failed: {e}")
        sys.exit(1)

    if getattr(args, "open_after", False) and out_file and out_file.is_file():
        if shutil.which("xdg-open"):
            subprocess.Popen(["xdg-open", str(out_file.resolve())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif shutil.which("open"):
            subprocess.Popen(["open", str(out_file.resolve())], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

if __name__ == "__main__":
    main()
