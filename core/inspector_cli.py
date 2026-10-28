"""
core/inspector_cli.py
Terminal-based Knowledge Base Inspector (kb-inspector) powered by Python rich.
Provides visual terminal inspection of resolved domain entities, legal provisions,
threat intelligence, forensic events, and relationship graphs from Markdown,
.kb.json manifests, or RO-Crate archives.
"""

import sys
import json
import zipfile
from pathlib import Path
from typing import Optional, List, Dict, Any

from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.tree import Tree
from rich.columns import Columns
from rich.text import Text
from rich import box

from core.kb.models import KnowledgePack, Entity, WidgetDescriptor
from core.kb.lifecycle import KnowledgeLifecycleManager
from core.bundler import is_md_style_html, extract_bundled_knowledge_pack, extract_bundled_markdown
from core.diagnostics import stderr_console, stdout_console


def load_knowledge_pack(target_path: Path) -> KnowledgePack:
    """
    Loads a KnowledgePack from:
      1. .md / .markdown file (via KnowledgeLifecycleManager)
      2. .kb.json or .json file directly
      3. .crate.zip / .zip archive (reads embedded report.kb.json)
      4. .html / .htm report bundled by md-style (reads embedded Knowledge Pack JSON)
    """
    if not target_path.exists():
        raise FileNotFoundError(f"Target file not found: {target_path}")

    ext = target_path.suffix.lower()

    # 1. ZIP / RO-Crate archive
    if ext == ".zip" or ".crate" in target_path.name:
        with zipfile.ZipFile(target_path, "r") as zf:
            candidates = ["report.kb.json", "knowledge_pack.json"]
            kb_name = next((c for c in candidates if c in zf.namelist()), None)
            if not kb_name:
                # Find any .kb.json
                kb_name = next((n for n in zf.namelist() if n.endswith(".kb.json")), None)
            if not kb_name:
                raise ValueError(f"No Knowledge Pack JSON found inside crate: {target_path.name}")
            data = json.loads(zf.read(kb_name).decode("utf-8"))
            return KnowledgePack.from_dict(data)

    # 2. JSON file directly
    if ext == ".json":
        data = json.loads(target_path.read_text(encoding="utf-8"))
        return KnowledgePack.from_dict(data)

    # 2b. HTML report bundled by md-style
    if ext in (".html", ".htm"):
        if not is_md_style_html(target_path):
            raise ValueError(f"Cannot inspect '{target_path.name}': Generic HTML file is not a report bundled by md-style.")
        kb_data = extract_bundled_knowledge_pack(target_path)
        if kb_data:
            return KnowledgePack.from_dict(kb_data)
        raw_md = extract_bundled_markdown(target_path)
        if raw_md:
            mgr = KnowledgeLifecycleManager(target_path)
            return mgr.sync(raw_md, allow_online=False)
        raise ValueError(f"No Knowledge Pack data or embedded Markdown found inside '{target_path.name}'.")

    # 3. Markdown source document
    mgr = KnowledgeLifecycleManager(target_path)
    loaded = mgr.load_existing_pack()
    if loaded and mgr.pack:
        return mgr.pack
    # If not yet persisted to disk, sync in memory (air-gap safe)
    content = target_path.read_text(encoding="utf-8")
    return mgr.sync(content, allow_online=False)


def render_kb_overview_table(pack: KnowledgePack, source_name: str, console: Optional[Console] = None) -> None:
    """Renders a comprehensive terminal dashboard table of all entities in the pack."""
    con = console or stdout_console

    table = Table(
        title=f"Knowledge Pack Entities — [bold cyan]{source_name}[/bold cyan] ({len(pack.entities)} total)",
        box=box.ROUNDED,
        header_style="bold magenta",
        title_justify="left"
    )

    table.add_column("Entity ID", style="bold cyan")
    table.add_column("Type", style="yellow")
    table.add_column("Domain", style="blue")
    table.add_column("Severity / Badge", justify="center")
    table.add_column("Title / Summary")
    table.add_column("Provenance Source", style="dim")

    severity_styles = {
        "CRITICAL": "[bold white on red] CRITICAL [/]",
        "HIGH": "[bold red] HIGH [/]",
        "MEDIUM": "[bold yellow] MEDIUM [/]",
        "LOW": "[green] LOW [/]",
        "INFO": "[cyan] INFO [/]"
    }

    # Sort entities by domain then type then ID
    sorted_entities = sorted(pack.entities.values(), key=lambda e: (e.domain, e.type, e.id))

    for ent in sorted_entities:
        sev_label = severity_styles.get(ent.severity, f"[{ent.severity}]")
        if ent.badge:
            short_badge = ent.badge if len(ent.badge) <= 20 else ent.badge[:18] + "…"
            badge_display = f"{sev_label}\n[dim]{short_badge}[/dim]"
        else:
            badge_display = sev_label

        summary_preview = ent.title or ent.summary
        if len(summary_preview) > 75:
            summary_preview = summary_preview[:72] + "..."

        source_label = ent.provenance.source if ent.provenance else "unknown"

        # Format long IDs (e.g. 64-char SHA256 hashes) cleanly
        id_display = ent.id
        if len(id_display) > 28:
            id_display = f"{id_display[:12]}…{id_display[-8:]}"

        table.add_row(
            id_display,
            ent.type.upper(),
            ent.domain,
            badge_display,
            f"[bold]{ent.title}[/bold]\n[dim]{ent.summary[:90] + '...' if len(ent.summary) > 90 else ent.summary}[/dim]",
            source_label
        )

    con.print()
    con.print(table)
    con.print(
        f"[dim]Tip: Inspect any individual entity in detail using: "
        f"[bold white]md-style inspect {source_name} <ENTITY-ID>[/bold white][/dim]\n"
    )


def find_entity(pack: KnowledgePack, query: str) -> Optional[Entity]:
    """Finds an entity by exact ID, label, alias, or case-insensitive partial match."""
    q = query.strip()
    q_low = q.lower()

    # 1. Exact ID match
    if q in pack.entities:
        return pack.entities[q]

    for ent in pack.entities.values():
        if ent.id.lower() == q_low or ent.label.lower() == q_low:
            return ent
        if any(a.lower() == q_low for a in ent.aliases):
            return ent

    # 2. Case-insensitive substring match
    for ent in pack.entities.values():
        if q_low in ent.id.lower() or q_low in ent.title.lower() or q_low in ent.label.lower():
            return ent
        if any(q_low in a.lower() for a in ent.aliases):
            return ent

    return None


def render_entity_card(ent: Entity, console: Optional[Console] = None) -> None:
    """Renders a rich, multi-panel terminal inspector card for a single entity."""
    con = console or stdout_console

    severity_colors = {
        "CRITICAL": "red",
        "HIGH": "bright_red",
        "MEDIUM": "yellow",
        "LOW": "green",
        "INFO": "cyan"
    }
    tone_color = severity_colors.get(ent.severity, "cyan")

    # 1. Header & Summary Panel
    header_title = f"[{tone_color} bold]{ent.title}[/{tone_color} bold]"
    header_subtitle = f"ID: [bold cyan]{ent.id}[/bold cyan]  •  Domain: [bold blue]{ent.domain}[/bold blue]  •  Type: [bold yellow]{ent.type.upper()}[/bold yellow]  •  Severity: [{tone_color}]{ent.severity}[/{tone_color}]"

    summary_text = ent.summary or "No summary description available."
    badge_str = f" [bold white on {tone_color}] {ent.badge} [/] " if ent.badge else ""

    con.print()
    con.print(
        Panel(
            f"{badge_str}\n\n{summary_text}",
            title=header_title,
            subtitle=header_subtitle,
            border_style=tone_color,
            box=box.ROUNDED,
            padding=(1, 2)
        )
    )

    # 2. Attributes Table
    if ent.attributes:
        attr_table = Table(
            title="Metadata Attributes",
            box=box.SIMPLE_HEAVY,
            show_header=True,
            header_style="bold cyan",
            expand=True
        )
        attr_table.add_column("Property", style="bold yellow", ratio=1)
        attr_table.add_column("Value", ratio=3)
        for k, v in ent.attributes.items():
            attr_table.add_row(str(k), str(v))
        con.print(attr_table)

    # 3. Widgets / Domain Cards
    for w in ent.widgets:
        w_type = w.widget_type
        w_data = w.data

        if w_type == "tactical_box":
            title = w.title or "Tactical Guidance"
            code_label = w_data.get("codeLabel", "Code / Notes")
            code_text = w_data.get("code", "")
            desc = w_data.get("description", "")
            body = ""
            if desc:
                body += f"{desc}\n\n"
            if code_text:
                body += f"[bold underline]{code_label}:[/bold underline]\n{code_text}"
            con.print(
                Panel(
                    body.strip(),
                    title=f"[bold green]■ {title}[/bold green]",
                    border_style="green",
                    box=box.SQUARE
                )
            )
        elif w_type == "qr_platba":
            acc = w_data.get("account", "N/A")
            iban = w_data.get("iban", "N/A")
            bank = w_data.get("bank", "N/A")
            spayd = w_data.get("spayd", "N/A")
            qr_content = (
                f"[bold cyan]Bankový účet:[/bold cyan] {acc} ({bank})\n"
                f"[bold cyan]IBAN:[/bold cyan]         {iban}\n"
                f"[bold cyan]SPAYD Kód:[/bold cyan]    [dim]{spayd}[/dim]\n\n"
                f"[italic dim](V HTML přehledu je zobrazen interaktivní vektorový SVG QR kód pro mobilní bankovnictví)[/italic dim]"
            )
            con.print(
                Panel(
                    qr_content,
                    title="[bold green]■ QR Platba (Standard ČBA SPAYD)[/bold green]",
                    border_style="cyan",
                    box=box.ROUNDED
                )
            )

    # 4. Relationships Graph Tree
    if ent.relationships:
        tree = Tree(f"[bold magenta]Entity Relationships Graph ({len(ent.relationships)} links)[/bold magenta]")
        for rel in ent.relationships:
            target = rel.get("target", "unknown")
            relation = rel.get("relation", "relates_to")
            tree.add(f"[cyan]{relation}[/cyan] ──► [bold yellow]{target}[/bold yellow]")
        con.print(tree)
        con.print()

    # 5. Official References & Registry Links
    if ent.references:
        ref_table = Table(
            title="Authoritative References & Public Registers",
            box=box.SIMPLE,
            show_header=False,
            expand=True
        )
        ref_table.add_column("Title", style="bold", ratio=2)
        ref_table.add_column("URL", style="underline cyan", ratio=3)
        for r in ent.references:
            ref_table.add_row(r.get("title", "Reference"), r.get("url", ""))
        con.print(ref_table)

    # 6. Provenance & Audit Trail
    if ent.provenance:
        prov = ent.provenance
        con.print(
            Panel(
                f"Source: [cyan]{prov.source}[/cyan]  •  Fetched At: [dim]{prov.fetched_at}[/dim]  •  Status: [green]{prov.status}[/green]  •  Manual Override: {'[yellow]YES[/yellow]' if prov.manual_override else '[dim]NO[/dim]'}",
                title="[dim]Provenance & Lineage[/dim]",
                border_style="dim",
                box=box.ROUNDED
            )
        )
    con.print()


def inspect_cli_entrypoint(target_path: Path, token_query: Optional[str] = None) -> None:
    """CLI entrypoint for md-style inspect command."""
    try:
        pack = load_knowledge_pack(target_path)
    except Exception as e:
        stderr_console.print(f"[bold red][ERROR][/bold red] Failed to load Knowledge Pack from '{target_path}': {e}")
        sys.exit(1)

    if not token_query:
        # Overview mode
        render_kb_overview_table(pack, target_path.name)
    else:
        # Token drilldown mode
        ent = find_entity(pack, token_query)
        if ent:
            render_entity_card(ent)
        else:
            stderr_console.print(f"\n[bold yellow][WARNING][/bold yellow] No entity matching '{token_query}' found in '{target_path.name}'.")
            stderr_console.print("[dim]Available entities in pack:[/dim]")
            for k in sorted(pack.entities.keys()):
                stderr_console.print(f"  • {k}")
            stderr_console.print()
            sys.exit(1)
