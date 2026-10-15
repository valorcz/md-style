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

from rich.table import Table
from rich.panel import Panel
from rich import box

from core.diagnostics import Colors, Diagnostics, stdout_console, stderr_console
from core.engine import ReportEngine, PipelineConfig, validate_input_file
from core.themes import ThemeResolver
from core.kb import KnowledgeLifecycleManager
from core.kb.sync import sync_all_catalogs
from core.kb.resolvers import get_resolver_descriptors

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
    parser.add_argument("-s", "--style", default=None, help="Style name or theme (default: from frontmatter or 'forensic')")
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
    parser.add_argument("--viewer", dest="interactive_viewer", action="store_true", default=None, help="Enable interactive Svelte viewer & annotator overlay (default: enabled unless disabled in frontmatter or theme)")
    parser.add_argument("--no-viewer", dest="interactive_viewer", action="store_false", help="Disable interactive Svelte viewer & annotator overlay (output pure static HTML)")
    parser.add_argument("--no-interactive", dest="interactive_viewer", action="store_false", help="Alias for --no-viewer")
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
    parser.add_argument(
        "--list-artifacts", "--list-resolvers",
        dest="list_artifacts",
        action="store_true",
        help="List all supported indicators, extractors, providers, and artifact families"
    )
    parser.add_argument(
        "--crate",
        dest="generate_crate",
        action="store_true",
        help="Package report as an RO-Crate (Research Object Crate v1.1) archive (.crate.zip)"
    )
    parser.add_argument(
        "--evidence",
        dest="evidence_path",
        default=None,
        help="Path to evidence file or directory to bundle inside the RO-Crate under evidence/"
    )
    parser.add_argument(
        "--verify-crate",
        dest="verify_crate_path",
        default=None,
        help="Verify structural and cryptographic (SHA-256) integrity of an RO-Crate package"
    )
    parser.add_argument("--kb-status", action="store_true", help="Display Knowledge Pack entity counts and provenance")
    parser.add_argument(
        "--kb-sync",
        action="store_true",
        help="Synchronize authoritative offline knowledge base catalogs (MITRE ATT&CK, Windows Events, EVTX channels)"
    )
    parser.add_argument(
        "--inspect",
        dest="inspect_token",
        nargs="?",
        const="",
        default=None,
        help="Inspect Knowledge Pack entities in terminal table or drill down into token (e.g. --inspect or --inspect CVE-2024-3094)"
    )
    parser.add_argument(
        "--preview",
        dest="preview_mode",
        action="store_true",
        help="Render Markdown preview directly in the terminal"
    )
    parser.add_argument(
        "--page",
        dest="preview_page",
        action="store_true",
        help="Page terminal preview through less / system pager"
    )
    # Theme tooling (Inspector, Linter, Scaffolder)
    parser.add_argument(
        "--theme-inspect",
        dest="theme_inspect_name",
        nargs="?",
        const="",
        default=None,
        help="Inspect theme inheritance cascade, CSS variables, and print rules (e.g. --theme-inspect or --theme-inspect forensic/cyber)"
    )
    parser.add_argument(
        "--theme-lint",
        dest="theme_lint_target",
        nargs="?",
        const="",
        default=None,
        help="Audit theme manifests, stylesheets, and Paged.js geometry (e.g. --theme-lint or --theme-lint forensic/cyber)"
    )
    parser.add_argument(
        "--theme-new",
        dest="theme_new_name",
        default=None,
        help="Scaffold a new custom theme directory with starter template (e.g. --theme-new custom/brand)"
    )

    parser.add_argument("-v", "--verbose", action="store_true", help="Verbose debug output")
    parser.add_argument("-q", "--quiet", action="store_true", help="Quiet output (errors only)")

    return parser

def list_available_styles() -> None:
    from core.theme_tool import ThemeInspector
    ThemeInspector().list_themes()

def list_available_artifacts() -> None:
    descriptors = get_resolver_descriptors()

    domain_titles = {
        "threat_intel": "THREAT INTELLIGENCE & VULNERABILITY ADVISORIES",
        "forensics": "DIGITAL FORENSICS & INCIDENT RESPONSE (DFIR)",
        "legal": "PUBLIC ADMINISTRATION & LEGAL CODES (SVJ / CZ / EU)",
        "finance": "BANKING & PAYMENTS (ČNB / SPAYD QR PLATBA)"
    }

    by_domain = {}
    for d in descriptors:
        dom = d.get("domain", "other")
        by_domain.setdefault(dom, []).append(d)

    stdout_console.print()
    stdout_console.print("[bold cyan]Supported Knowledge Pack Artifacts, Extractors & Providers[/bold cyan]\n")

    for dom, items in by_domain.items():
        title = domain_titles.get(dom, dom.upper())
        table = Table(
            title=f"■ {title}",
            box=box.ROUNDED,
            header_style="bold yellow",
            title_justify="left",
            expand=True
        )
        table.add_column("Artifact Family", style="bold white", no_wrap=True)
        table.add_column("Description", style="white", ratio=2)
        table.add_column("Extractor Patterns", style="yellow", ratio=2)
        table.add_column("Authority / Provider", style="cyan", ratio=2)
        table.add_column("Resolution Mode", justify="center", no_wrap=True)

        for it in items:
            patterns = ", ".join(f"`{p}`" for p in it["patterns"])
            mode_badge = "[bold green]Online Dynamic[/bold green]" if it.get("online_dynamic") else "[bold blue]Air-Gap SSOT[/bold blue]"
            table.add_row(it["name"].upper(), it["title"], patterns, it["provider"], mode_badge)

        stdout_console.print(table)
        stdout_console.print()

def show_kb_status(input_path: Path) -> None:
    mgr = KnowledgeLifecycleManager(input_path)
    loaded = mgr.load_existing_pack()
    if not loaded:
        stdout_console.print(f"[bold yellow][WARNING][/bold yellow] No existing Knowledge Pack found at [dim]{mgr.kb_json_path}[/dim]")
        return

    pack = mgr.pack
    
    # Entity breakdown
    by_type = {}
    by_domain = {}
    manual_overrides = 0
    for ent in pack.entities.values():
        by_type[ent.type] = by_type.get(ent.type, 0) + 1
        by_domain[ent.domain] = by_domain.get(ent.domain, 0) + 1
        if ent.provenance and ent.provenance.manual_override:
            manual_overrides += 1

    summary_table = Table.grid(padding=(0, 2))
    summary_table.add_column(style="bold cyan")
    summary_table.add_column()
    summary_table.add_row("Pack File:", str(mgr.kb_json_path))
    summary_table.add_row("Total Entities:", f"[bold white]{len(pack.entities)}[/bold white]")
    summary_table.add_row("Generated At:", str(pack.generated_at))
    summary_table.add_row("Manual Overrides:", f"[bold yellow]{manual_overrides}[/bold yellow]" if manual_overrides else "0")

    stdout_console.print()
    stdout_console.print(Panel(summary_table, title=f"Knowledge Pack Status — [bold cyan]{input_path.name}[/bold cyan]", box=box.ROUNDED))

    # Table breakdown by domain & type
    breakdown_table = Table(title="Entities by Domain & Type", box=box.SIMPLE_HEAVY, header_style="bold magenta")
    breakdown_table.add_column("Category", style="bold yellow")
    breakdown_table.add_column("Distribution Breakdown", style="white")

    dom_str = ", ".join(f"[bold cyan]{k}[/bold cyan]: {v}" for k, v in sorted(by_domain.items()))
    type_str = ", ".join(f"[bold green]{k}[/bold green]: {v}" for k, v in sorted(by_type.items()))
    breakdown_table.add_row("Domains", dom_str)
    breakdown_table.add_row("Types", type_str)

    stdout_console.print(breakdown_table)

    if pack.sources_digest:
        src_table = Table(title="Sources Digest Integrity", box=box.SIMPLE, header_style="bold")
        src_table.add_column("Source", style="cyan")
        src_table.add_column("SHA-256 Digest", style="dim")
        for src, dig in pack.sources_digest.items():
            src_table.add_row(src, dig)
        stdout_console.print(src_table)
    stdout_console.print()

def main():
    # 1. Shorthand subcommands: md-style inspect <target> [token] / md-style preview <file> [--page]
    if len(sys.argv) > 1 and sys.argv[1] == "inspect":
        target = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("-") else None
        token = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("-") else None
        if not target:
            Diagnostics.error("Usage: md-style inspect <file.md|file.kb.json|file.crate.zip> [token]")
            sys.exit(1)
        from core.inspector_cli import inspect_cli_entrypoint
        inspect_cli_entrypoint(Path(target), token_query=token)
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] == "preview":
        target = sys.argv[2] if len(sys.argv) > 2 and not sys.argv[2].startswith("-") else None
        if not target:
            Diagnostics.error("Usage: md-style preview <file.md> [--page]")
            sys.exit(1)
        use_pager = "--page" in sys.argv
        from core.preview_cli import preview_markdown
        preview_markdown(Path(target), use_pager=use_pager)
        sys.exit(0)

    if len(sys.argv) > 1 and sys.argv[1] in {"theme", "themes"}:
        subcmd = sys.argv[2] if len(sys.argv) > 2 else "list"
        arg = sys.argv[3] if len(sys.argv) > 3 and not sys.argv[3].startswith("-") else None
        from core.theme_tool import ThemeInspector, ThemeLinter, ThemeScaffolder, print_lint_report

        if subcmd in {"list", "ls"}:
            ThemeInspector().list_themes()
            sys.exit(0)
        elif subcmd in {"inspect", "info"}:
            if not arg:
                ThemeInspector().list_themes()
            else:
                ThemeInspector().inspect_theme(arg)
            sys.exit(0)
        elif subcmd in {"lint", "check"}:
            linter = ThemeLinter()
            msgs = linter.lint_theme_name(arg) if arg else linter.lint_all()
            ok = print_lint_report(msgs)
            sys.exit(0 if ok else 1)
        elif subcmd in {"new", "create", "scaffold"}:
            if not arg:
                Diagnostics.error("Usage: md-style theme new <family/name> [--extends <base>]")
                sys.exit(1)
            extends = "base"
            if "--extends" in sys.argv:
                ext_idx = sys.argv.index("--extends")
                if ext_idx + 1 < len(sys.argv):
                    extends = sys.argv[ext_idx + 1]
            scaffolder = ThemeScaffolder()
            res_dir = scaffolder.scaffold(arg, extends=extends)
            stdout_console.print(f"\n[bold green]✓ New theme scaffolded successfully:[/] {res_dir}")
            stdout_console.print(f"  • Created manifest: [cyan]{res_dir}/theme.yaml[/cyan]")
            stdout_console.print(f"  • Created stylesheet: [cyan]{res_dir}/{res_dir.name}.css[/cyan]\n")
            sys.exit(0)
        else:
            Diagnostics.error(f"Unknown theme action '{subcmd}'. Choose from: list, inspect, lint, new.")
            sys.exit(1)

    parser = build_parser()
    args = parser.parse_args()

    if args.verbose:
        import rich.traceback
        rich.traceback.install(show_locals=True, extra_lines=1)

    if args.list_styles:
        list_available_styles()
        sys.exit(0)

    if args.theme_inspect_name is not None:
        from core.theme_tool import ThemeInspector
        inspector = ThemeInspector()
        if args.theme_inspect_name:
            inspector.inspect_theme(args.theme_inspect_name)
        else:
            inspector.list_themes()
        sys.exit(0)

    if args.theme_lint_target is not None:
        from core.theme_tool import ThemeLinter, print_lint_report
        linter = ThemeLinter()
        msgs = linter.lint_theme_name(args.theme_lint_target) if args.theme_lint_target else linter.lint_all()
        ok = print_lint_report(msgs)
        sys.exit(0 if ok else 1)

    if args.theme_new_name:
        from core.theme_tool import ThemeScaffolder
        scaffolder = ThemeScaffolder()
        res_dir = scaffolder.scaffold(args.theme_new_name)
        stdout_console.print(f"\n[bold green]✓ New theme scaffolded successfully:[/] {res_dir}")
        stdout_console.print(f"  • Created manifest: [cyan]{res_dir}/theme.yaml[/cyan]")
        stdout_console.print(f"  • Created stylesheet: [cyan]{res_dir}/{res_dir.name}.css[/cyan]\n")
        sys.exit(0)

    if args.list_artifacts:
        list_available_artifacts()
        sys.exit(0)

    if args.verify_crate_path:
        from core.crate import verify_ro_crate
        crate_p = Path(args.verify_crate_path)
        is_valid, errors = verify_ro_crate(crate_p)
        if is_valid:
            stdout_console.print(f"\n[bold green]✓ RO-Crate verification successful:[/] {crate_p}")
            stdout_console.print("  • All declared payload files exist and match their SHA-256 digests.")
            stdout_console.print("  • Conforms to RO-Crate 1.1 JSON-LD specification.\n")
            sys.exit(0)
        else:
            stderr_console.print(f"\n[bold red]✗ RO-Crate verification failed:[/] {crate_p}")
            for err in errors:
                stderr_console.print(f"  • [yellow]{err}[/]")
            stderr_console.print()
            sys.exit(1)

    if args.kb_sync:
        results = sync_all_catalogs(verbose=not args.quiet)
        stdout_console.print(f"\n[bold green]Knowledge base catalogs synchronized successfully:[/]")
        for name, count in results.items():
            stdout_console.print(f"  • [cyan]{name}[/]: {count} records")
        stdout_console.print()
        sys.exit(0)

    # Flags shorthand for inspect and preview:
    if args.inspect_token is not None:
        if not args.input:
            Diagnostics.error("Usage: md-style <file.md|file.kb.json|file.crate.zip> --inspect [token]")
            sys.exit(1)
        from core.inspector_cli import inspect_cli_entrypoint
        inspect_cli_entrypoint(Path(args.input), token_query=args.inspect_token or None)
        sys.exit(0)

    if args.preview_mode:
        if not args.input:
            Diagnostics.error("Usage: md-style <file.md> --preview [--page]")
            sys.exit(1)
        from core.preview_cli import preview_markdown
        preview_markdown(Path(args.input), use_pager=args.preview_page)
        sys.exit(0)

    if not args.input:
        parser.print_help()
        sys.exit(1)

    input_path = Path(args.input)
    try:
        validate_input_file(input_path)
    except (FileNotFoundError, ValueError) as e:
        Diagnostics.error(str(e))
        sys.exit(1)

    if args.kb_status:
        show_kb_status(input_path)
        sys.exit(0)

    output_target = Path(args.output_opt or args.output) if (args.output_opt or args.output) else None
    generate_pdf = args.generate_pdf
    if output_target and output_target.suffix.lower() == ".pdf":
        generate_pdf = True

    generate_crate = args.generate_crate
    if output_target and str(output_target).lower().endswith((".zip", ".crate.zip")):
        generate_crate = True

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
        generate_crate=generate_crate,
        evidence_path=Path(args.evidence_path) if args.evidence_path else None,
        interactive_viewer=args.interactive_viewer,
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
