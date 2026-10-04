"""
core/cli.py
Native CLI entrypoint for md-style / md-to-report.
Orchestrates pre-flight checks, argument parsing, inspection, and compilation.
"""

import sys
import os
import shutil
import subprocess
import argparse
from pathlib import Path
from typing import Optional

from core.config import PROJECT_DIR, STYLE_CATEGORIES
from core.diagnostics import Colors, Diagnostics
from core.engine import ReportEngine, PipelineConfig

def check_prerequisites(generate_pdf: bool = False, enable_mermaid: bool = True) -> None:
    """Verifies external system tools required for compilation."""
    if not shutil.which("pandoc"):
        Diagnostics.error(
            "pandoc is not installed or not in PATH.\n"
            "Please install pandoc (e.g. 'brew install pandoc' or 'apt install pandoc')."
        )
        sys.exit(1)

    if enable_mermaid and not (shutil.which("bun") or shutil.which("node")):
        Diagnostics.warn(
            "Neither 'bun' nor 'node' found in PATH. Static Mermaid rendering may fail fallback."
        )

    if generate_pdf:
        has_chrome = any(shutil.which(cmd) for cmd in [
            "chromium", "chromium-browser", "google-chrome",
            "google-chrome-stable", "brave", "microsoft-edge"
        ])
        has_weasyprint = shutil.which("weasyprint") is not None
        if not (has_chrome or has_weasyprint):
            Diagnostics.warn(
                "Neither Chromium nor WeasyPrint was found. PDF generation might fail."
            )

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="md-to-report",
        description="Professional Markdown-to-HTML & PDF Report Generator for Pandoc",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  uv run md-to-report report.md -s forensic-cyber -o output.html
  uv run md-to-report report.md -s svj-modern --pdf
  uv run md-to-report report.md --inspect
  uv run md-to-report --list-styles
        """
    )

    parser.add_argument("input", nargs="?", default=None, help="Source Markdown document")
    parser.add_argument("output", nargs="?", default=None, help="Target HTML/PDF file")
    parser.add_argument("-o", "--output", dest="output_opt", help="Target HTML/PDF file")
    parser.add_argument("-s", "--style", help="Style name or custom CSS path (e.g. forensic-cyber, svj-modern)")
    parser.add_argument("-t", "--title", help="Override document title")
    parser.add_argument("-l", "--lang", help="Override document language (e.g. cs, en, sk, de)")
    
    # TOC
    parser.add_argument("--toc", action="store_true", default=True, help="Enable Table of Contents (default: True)")
    parser.add_argument("--no-toc", dest="toc", action="store_false", help="Disable Table of Contents")
    parser.add_argument("--toc-depth", type=int, default=3, help="TOC heading depth (default: 3)")
    parser.add_argument("-N", "--number-sections", action="store_true", help="Auto-number sections")

    # Layout & Output Modes
    parser.add_argument("--paged", action="store_true", help="Enable Paged.js preview mode")
    parser.add_argument("--print", dest="print_mode", action="store_true", help="Enable Native Print mode")
    parser.add_argument("-p", "--pdf", dest="generate_pdf", action="store_true", help="Generate PDF directly")
    parser.add_argument("--pdf-engine", help="Explicit PDF engine (chromium, weasyprint)")
    parser.add_argument("--highlight-style", default="kate", help="Pandoc syntax highlighting theme (default: kate)")
    parser.add_argument("--embed-resources", action="store_true", default=True, help="Embed resources into self-contained HTML (default: True)")
    parser.add_argument("--no-embed-resources", dest="embed_resources", action="store_false", help="Link external stylesheets instead of inlining")
    parser.add_argument("--open", dest="open_after", action="store_true", help="Open generated report in default viewer")

    # Threat Intel & Offline Flags
    parser.add_argument("-k", "--knowledge", dest="knowledge_path", default=None, help="Path to custom knowledge directory or YAML/JSON file")
    parser.add_argument("--enrich", dest="enrich", action="store_true", default=None, help="Explicitly enable Stage 2 indicator enrichment")
    parser.add_argument("--no-enrich", dest="enrich", action="store_false", help="Explicitly disable Stage 2 indicator enrichment")
    parser.add_argument("--offline", dest="allow_online", action="store_false", default=True, help="Disable on-demand online scraping for indicators")
    parser.add_argument("--no-mermaid", dest="enable_mermaid", action="store_false", default=True, help="Disable Mermaid diagram rendering")
    parser.add_argument("--no-auto-nowrap", dest="auto_nowrap", action="store_false", default=True, help="Disable auto-nowrap on tables")

    # Diagnostic & Inspection
    parser.add_argument("--inspect", action="store_true", help="Dry-run diagnostic scan: inspect enrichments, AST changes, and providers without compiling")
    parser.add_argument("--list-styles", action="store_true", help="List all available built-in document styles")
    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose debug output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet output (errors only)")

    return parser

def list_available_styles() -> None:
    print(f"\n{Colors.BOLD}Available md-style Themes:{Colors.RESET}")
    for cat_name, styles in STYLE_CATEGORIES.items():
        print(f"\n  {Colors.CYAN}{cat_name}:{Colors.RESET}")
        for s in styles:
            print(f"    - {Colors.GREEN}{s}{Colors.RESET}")
    print()

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

    # Inspection dry-run mode
    if args.inspect:
        from core.inspector import main as inspector_main
        sys.argv = [sys.argv[0], str(input_path)]
        inspector_main()
        sys.exit(0)

    output_target = Path(args.output_opt or args.output) if (args.output_opt or args.output) else None
    generate_pdf = args.generate_pdf
    if output_target and output_target.suffix.lower() == ".pdf":
        generate_pdf = True

    # Prerequisite verification
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
        highlight_style=args.highlight_style,
        paged=args.paged,
        print_mode=args.print_mode,
        generate_pdf=generate_pdf,
        pdf_engine=args.pdf_engine,
        enable_mermaid=args.enable_mermaid,
        auto_nowrap=args.auto_nowrap,
        allow_online=args.allow_online,
        enrich=args.enrich,
        knowledge_path=Path(args.knowledge_path) if args.knowledge_path else None,
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
