"""
core/lint/reporter.py
Publication-grade Rich terminal reporter for prose, rhythm, and typography linting.
"""

from typing import Optional
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

from core.diagnostics import stdout_console
from core.lint.models import LintResult


def format_grade(grade: str) -> str:
    if grade in ("A+", "A"):
        return f"[bold green]{grade}[/bold green]"
    elif grade == "B":
        return f"[bold cyan]{grade}[/bold cyan]"
    elif grade == "C":
        return f"[bold yellow]{grade}[/bold yellow]"
    elif grade == "D":
        return f"[bold orange3]{grade}[/bold orange3]"
    else:
        return f"[bold red]{grade}[/bold red]"


def print_lint_report(result: LintResult, verbose: bool = False) -> None:
    """Renders a structured, publication-grade Rich terminal report."""
    p = result.profile
    is_czech = result.lang in ("cs", "sk")

    # Header Panel
    title_text = "Prose & Typography Audit" if not is_czech else "Audit kvality prózy a typografie"
    
    header_table = Table.grid(padding=(0, 2))
    header_table.add_column(style="bold cyan")
    header_table.add_column()

    file_display = str(result.file_path) if result.file_path else "(memory buffer)"
    header_table.add_row("Document:" if not is_czech else "Dokument:", f"[bold white]{file_display}[/bold white]")
    header_table.add_row(
        "Profile:" if not is_czech else "Profil:",
        f"[bold magenta]{p.name}[/bold magenta] ({p.title}) [dim][{result.detected_via}][/dim]"
    )
    header_table.add_row("Description:" if not is_czech else "Popis:", f"[dim]{p.description}[/dim]")

    stdout_console.print()
    stdout_console.print(Panel(header_table, title=f"■ [bold white]{title_text}[/bold white]", box=box.ROUNDED))

    # Metrics Table
    metrics_table = Table(
        title="Document Scope & Formatting Metrics" if not is_czech else "Metriky rozsahu a hustoty formátování",
        box=box.SIMPLE_HEAVY,
        header_style="bold yellow",
        expand=True
    )
    metrics_table.add_column("Metric" if not is_czech else "Metrika", style="bold white", ratio=3)
    metrics_table.add_column("Count / Density" if not is_czech else "Počet / Hustota", ratio=3)
    metrics_table.add_column("Target Range" if not is_czech else "Cílové rozpětí", ratio=3)
    metrics_table.add_column("Status", justify="center", ratio=2)

    # Word count
    metrics_table.add_row(
        "Total Words" if not is_czech else "Celkový rozsah slov",
        f"[bold white]{result.total_words:,}[/bold white] words",
        "—",
        "[bold green]OK[/bold green]"
    )

    # Bold density
    b_color = "red" if result.bold_density > p.fail_bold else ("yellow" if result.bold_density > p.max_bold else "green")
    b_status = "[bold red]FAIL[/bold red]" if result.bold_density > p.fail_bold else ("[bold yellow]WARN[/bold yellow]" if result.bold_density > p.max_bold else "[bold green]PASS[/bold green]")
    metrics_table.add_row(
        "Bold Text (**bold**)" if not is_czech else "Tučný text (**bold**)",
        f"{result.bold_words:,} words ([{b_color}]{result.bold_density:.1f}%[/{b_color}])",
        f"{p.target_bold[0]:.0f}–{p.target_bold[1]:.0f}% (max: {p.max_bold:.0f}%)",
        b_status
    )

    # Italic density
    i_color = "red" if result.italic_density > p.fail_italic else ("yellow" if result.italic_density > p.max_italic else "green")
    i_status = "[bold red]FAIL[/bold red]" if result.italic_density > p.fail_italic else ("[bold yellow]WARN[/bold yellow]" if result.italic_density > p.max_italic else "[bold green]PASS[/bold green]")
    metrics_table.add_row(
        "Italic Text (*italic*)" if not is_czech else "Kurzíva (*italic*)",
        f"{result.italic_words:,} words ([{i_color}]{result.italic_density:.1f}%[/{i_color}])",
        f"{p.target_italic[0]:.0f}–{p.target_italic[1]:.0f}% (max: {p.max_italic:.0f}%)",
        i_status
    )

    # Score summary
    metrics_table.add_row(
        "Quality Score & Grade" if not is_czech else "Výsledné skóre a známka",
        f"[bold]{result.score:.1f}[/bold] / 100",
        f"Grade: {format_grade(result.grade)}",
        "[bold green]PASS[/bold green]" if result.score >= 80 else "[bold yellow]NEEDS WORK[/bold yellow]"
    )

    stdout_console.print(metrics_table)
    stdout_console.print()

    # Readability Table
    if result.readability:
        r = result.readability
        read_table = Table(
            title="Readability & Linguistic Complexity" if not is_czech else "Srozumitelnost a textová náročnost",
            box=box.SIMPLE_HEAVY,
            header_style="bold cyan",
            expand=True
        )
        read_table.add_column("Formula / Index" if not is_czech else "Metrika / Index", style="bold white", ratio=3)
        read_table.add_column("Score / Value" if not is_czech else "Hodnota", ratio=3)
        read_table.add_column("Interpretation & Comprehension Level" if not is_czech else "Interpretace a úroveň srozumitelnosti", ratio=5)

        if r.lang == "en":
            read_table.add_row(
                "Flesch Reading Ease",
                f"[bold cyan]{r.flesch_reading_ease:.1f}[/bold cyan] / 100",
                f"[bold white]{r.interpretation}[/bold white]"
            )
            read_table.add_row(
                "Flesch-Kincaid Grade",
                f"[bold magenta]Grade {r.flesch_kincaid_grade:.1f}[/bold magenta]",
                f"Reading age: ~{r.flesch_kincaid_grade + 5:.0f} years"
            )
            read_table.add_row(
                "Automated Readability (ARI)",
                f"[bold]{r.automated_readability_index:.1f}[/bold]",
                f"Surface character ratio: {r.avg_word_characters:.1f} chars/word"
            )
            read_table.add_row(
                "Structural Density",
                f"{r.avg_sentence_words:.1f} words/sentence",
                f"{r.avg_word_syllables:.2f} syllables/word • {r.complex_word_ratio:.1f}% complex words (≥3 syll)"
            )
        else:
            read_table.add_row(
                "Mistríkův index srozumitelnosti",
                f"[bold cyan]{r.mistrik_index:.1f}[/bold cyan] bodů",
                f"[bold white]{r.interpretation}[/bold white]"
            )
            read_table.add_row(
                "Český Fleschův index",
                f"[bold magenta]{r.czech_flesch_index:.1f}[/bold magenta] / 100",
                f"Kalibrováno pro slovanskou morfologii"
            )
            read_table.add_row(
                "Struktura a hustota vět",
                f"{r.avg_sentence_words:.1f} slov/větu",
                f"{r.avg_word_syllables:.2f} slabik/slovo • {r.complex_word_ratio:.1f}% dlouhých slov (≥4 slabik)"
            )

        stdout_console.print(read_table)
        stdout_console.print()

    # Issues List
    warns = [i for i in result.issues if i.severity in ("FAIL", "WARN")]
    infos = [i for i in result.issues if i.severity == "INFO"]

    displayed_issues = warns + (infos if verbose else [])

    if not result.issues:
        ok_msg = f"✓ Document fully complies with '{p.name}' publication criteria." if not is_czech else f"✓ Dokument plně vyhovuje pravidlům profilu '{p.name}'."
        stdout_console.print(f"[bold green]{ok_msg}[/bold green]\n")
        return

    issues_title = f"Findings & Action Items ({len(result.issues)})" if not is_czech else f"Nalezené podněty ke zlepšení ({len(result.issues)})"
    stdout_console.print(f"[bold white]{issues_title}[/bold white]")

    for issue in displayed_issues:
        loc = f"L{issue.line:4d} " if issue.line else "GLOBAL "
        if issue.severity == "FAIL":
            sev_badge = "[bold red]FAIL[/bold red]"
        elif issue.severity == "WARN":
            sev_badge = "[bold yellow]WARN[/bold yellow]"
        else:
            sev_badge = "[bold blue]INFO[/bold blue]"

        stdout_console.print(f"   [dim]{loc}[/dim][{sev_badge}] [bold white][{issue.code}][/bold white] {issue.message}")
        if issue.snippet and verbose:
            stdout_console.print(f"          [dim]↳ {issue.snippet}[/dim]")

    if not verbose and infos:
        info_note = (
            f"\n   [dim]... and {len(infos)} minor informational recommendations (view with --verbose / -v).[/dim]"
            if not is_czech
            else f"\n   [dim]... a {len(infos)} drobných doporučení (zobrazíte volbou --verbose / -v).[/dim]"
        )
        stdout_console.print(info_note)

    stdout_console.print()
