"""
core/preview_cli.py
Terminal Markdown Previewer powered by Python rich.
Renders Markdown documents in the terminal with styled typography,
executive dossier header panels, Pygments syntax highlighting, and optional paging.
Supports Markdown files (.md), md-style bundled HTML reports (.html), and RO-Crates (.crate.zip).
"""

import sys
import re
import zipfile
from pathlib import Path
from typing import Optional

from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.markdown import Markdown
from rich import box

from core.parser.engine import MarkdownParser
from core.bundler import is_md_style_html, extract_bundled_markdown
from core.diagnostics import stderr_console, stdout_console


def preview_markdown(input_path: Path, use_pager: bool = False, console: Optional[Console] = None) -> None:
    """
    Renders a Markdown report directly into the terminal with rich formatting.
    Accepts:
      1. Markdown documents (.md, .markdown, .txt)
      2. md-style bundled HTML reports (.html, .htm) containing embedded Markdown
      3. RO-Crate archives (.crate.zip, .zip) containing report.md
    """
    con = console or stdout_console

    if not input_path.exists():
        stderr_console.print(f"[bold red][ERROR][/bold red] File not found: {input_path}")
        sys.exit(1)

    if not input_path.is_file():
        stderr_console.print(f"[bold red][ERROR][/bold red] Target path is not a regular file: {input_path}")
        sys.exit(1)

    ext = input_path.suffix.lower()
    source_origin_note: Optional[str] = None
    raw_text: str = ""

    # Check for binary file (unless ZIP archive)
    if ext not in (".zip",) and not input_path.name.endswith(".crate.zip") and ".crate" not in input_path.name:
        try:
            with open(input_path, "rb") as f:
                head = f.read(4096)
                if b"\x00" in head:
                    stderr_console.print(
                        f"[bold red][ERROR][/bold red] Cannot preview '{input_path.name}': "
                        f"Target appears to be a binary file, not a text or Markdown document."
                    )
                    sys.exit(1)
                if head.startswith(b"%PDF-"):
                    stderr_console.print(
                        f"[bold red][ERROR][/bold red] Cannot preview '{input_path.name}': "
                        f"PDF documents cannot be previewed as Markdown."
                    )
                    sys.exit(1)
        except Exception as e:
            stderr_console.print(f"[bold red][ERROR][/bold red] Cannot read file '{input_path.name}': {e}")
            sys.exit(1)

    # 1. HTML file handling
    if ext in (".html", ".htm"):
        if not is_md_style_html(input_path):
            stderr_console.print(
                f"[bold red][ERROR][/bold red] Cannot preview '{input_path.name}': "
                f"Generic HTML files are not supported. "
                f"md-style preview supports Markdown documents or HTML reports bundled by md-style."
            )
            sys.exit(1)

        extracted = extract_bundled_markdown(input_path)
        if not extracted:
            stderr_console.print(
                f"[bold yellow][WARNING][/bold yellow] HTML report '{input_path.name}' is an md-style bundle, "
                f"but embedded Markdown source was disabled during generation (--no-embed-source)."
            )
            sys.exit(1)

        raw_text = extracted
        source_origin_note = f"Extracted from md-style HTML bundle ({input_path.name})"

    # 2. RO-Crate ZIP archive handling
    elif ext == ".zip" or ".crate" in input_path.name:
        try:
            with zipfile.ZipFile(input_path, "r") as zf:
                candidates = ["report.md", "source.md", "input.md"]
                md_entry = next((c for c in candidates if c in zf.namelist()), None)
                if not md_entry:
                    md_entry = next((n for n in zf.namelist() if n.endswith(".md")), None)
                if not md_entry:
                    stderr_console.print(
                        f"[bold red][ERROR][/bold red] No Markdown source document found inside archive '{input_path.name}'."
                    )
                    sys.exit(1)
                raw_text = zf.read(md_entry).decode("utf-8", errors="replace")
                source_origin_note = f"Extracted from RO-Crate archive ({input_path.name} : {md_entry})"
        except Exception as e:
            stderr_console.print(f"[bold red][ERROR][/bold red] Failed to read archive '{input_path.name}': {e}")
            sys.exit(1)

    # 3. Markdown and text document handling
    elif ext in (".md", ".markdown", ".txt"):
        try:
            raw_text = input_path.read_text(encoding="utf-8")
        except Exception as e:
            stderr_console.print(f"[bold red][ERROR][/bold red] Failed to read '{input_path.name}': {e}")
            sys.exit(1)

    # 4. Disallowed / unsupported format
    else:
        stderr_console.print(
            f"[bold red][ERROR][/bold red] Unsupported file format '{ext}' for '{input_path.name}'. "
            f"md-style preview expects Markdown (.md, .markdown, .txt), an md-style bundled HTML report (.html), or an RO-Crate archive (.crate.zip)."
        )
        sys.exit(1)

    # Parse frontmatter
    temp_parser = MarkdownParser()
    cleaned_content, frontmatter = temp_parser.parse_frontmatter(raw_text)

    # Document title
    title = frontmatter.get("title")
    if not title:
        h1_match = re.search(r"^#\s+(.+)$", cleaned_content, re.MULTILINE)
        title = h1_match.group(1).strip() if h1_match else input_path.stem

    author = frontmatter.get("author") or frontmatter.get("examiner") or ""
    date = frontmatter.get("date") or ""
    style = frontmatter.get("style") or frontmatter.get("theme") or "forensic"
    abstract = frontmatter.get("abstract") or frontmatter.get("description") or ""

    def render_body():
        subtitle = f"[dim]Document Dossier • {source_origin_note or input_path.name}[/dim]"
        # 1. Frontmatter dossier header
        if frontmatter:
            meta_table = Table.grid(padding=(0, 2))
            meta_table.add_column(style="bold yellow")
            meta_table.add_column()

            if author:
                meta_table.add_row("Author / Examiner:", str(author))
            if date:
                meta_table.add_row("Date:", str(date))
            meta_table.add_row("Style Theme:", f"[bold cyan]{style}[/bold cyan]")
            if frontmatter.get("lang"):
                meta_table.add_row("Language:", str(frontmatter.get("lang")).upper())
            if source_origin_note:
                meta_table.add_row("Source:", f"[green]{source_origin_note}[/green]")

            if abstract:
                con.print(
                    Panel(
                        meta_table,
                        title=f"[bold cyan]■ {title}[/bold cyan]",
                        subtitle=subtitle,
                        box=box.ROUNDED,
                        border_style="cyan"
                    )
                )
                con.print(
                    Panel(
                        str(abstract).strip(),
                        title="[bold green]■ EXECUTIVE SUMMARY[/bold green]",
                        box=box.SQUARE,
                        border_style="green"
                    )
                )
            else:
                con.print(
                    Panel(
                        meta_table,
                        title=f"[bold cyan]■ {title}[/bold cyan]",
                        subtitle=subtitle,
                        box=box.ROUNDED,
                        border_style="cyan"
                    )
                )
        else:
            con.print(
                Panel(
                    f"[bold white]{title}[/bold white]",
                    subtitle=subtitle,
                    box=box.ROUNDED,
                    border_style="cyan"
                )
            )

        # 2. Render Markdown content
        con.print()
        md = Markdown(cleaned_content, code_theme="one-dark")
        con.print(md)
        con.print()

    if use_pager:
        with con.pager(styles=True):
            render_body()
    else:
        render_body()
