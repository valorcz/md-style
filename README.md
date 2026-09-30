# Markdown Report Styler (`md-style`)

> A robust, modern document generation toolchain for transforming Markdown into publication-ready **Forensic & DFIR Reports, Civic & Building Association (SVJ) Notices, Academic Reports, and Corporate Memos** using Pandoc.

---

## Highlights

- **Authoritative Typography & Themes**:
  - Curated font pairings (Roboto Slab / Merriweather, Plus Jakarta Sans / Inter, Courier Prime).
  - Pre-built themes tailored for specific document genres (forensic, SVJ notices, academic, memos).
- **Dual Layout Engines**:
  - **Native Print (`--print`)**: Zero-JS W3C `@media print` engine. Fast (<3s), compact (~400KB), pixel-perfect for physical paper and PDF export.
  - **Paged.js Polyfill (`--paged`)**: Browser preview engine simulating real A4 paper sheets with drop shadows and running headers/footers on screen.
- **Specialized Forensic & Technical Features**:
  - Monospace terminal blocks with macOS-style window controls and automatic language badges.
  - Unwrapped timestamp tables (`filters/table-nowrap.lua`) ensuring dates and hashes never wrap awkwardly across lines.
  - Severity status badges (`TLP:AMBER`, `CRITICAL FINDING`, etc.).
- **Civic & SVJ Assembly Automation**:
  - Dynamic inlined Table of Contents (`[[TOC]]`).
  - Strict first-page notice board isolation (suppressing headers and footers on page 1).
  - Guaranteed page break before agenda details.
  - Proposal callouts (`***Návrh výboru:***`) and optional voting resolution cards.
- **Fully Self-Contained Output**:
  - By default, inlines all stylesheets, web fonts, and assets into a single portable `.html` file.

---

## Available Themes & Styles

`md-style` includes pre-built, production-ready themes designed for distinct document types:

| Theme Name | Frontmatter | Purpose & Visual Identity |
|---|---|---|
| **Forensic** (default) | `style: forensic` | High-contrast DFIR investigation reports, TLP status badges, code terminal blocks, cryptographic hash registers. |
| **SVJ Modern** | `style: svj-modern` | Contemporary architectural theme for building assemblies: sans-serif typography, meeting key info card grid (Date, Time, Place), timeline agenda, and clean committee recommendation callouts. |
| **SVJ Community** | `style: svj-community` | Intergenerational & accessible design (young families & seniors 75+): WCAG AAA contrast, generous 11.5pt type scale, relaxed line height (1.72), large scannable meeting cards, and high-visibility proposal callouts. |
| **SVJ Ballot** | `style: svj-ballot` | Extends `svj-modern` with interactive & printable voting resolution cards featuring ballot checkboxes (`☐ PRO`, `☐ PROTI`, `☐ ZDRŽEL SE`). |
| **SVJ Typewriter** | `style: svj-typewriter` | Retro pre-1989 Czechoslovak municipal typewriter aesthetic (Consul mechanical font, original palette, red-ribbon motion callouts, typed table grids). |
| **SVJ Classic** | `style: svj-invitation` | Traditional serif assembly notices (*Pozvánka na shromáždění SVJ*), deep navy/teal/amber palette, proposal callouts. |
| **School Report** | `style: school` | Academic progress assessments, course rubrics, student dossier grids, booktabs tables, faculty signatures. |
| **Office Announcement** | `style: announcement` | Corporate executive memorandums, `TO/FROM/DATE/SUBJECT` header block, urgency banners, action task checklists. |
| **Family & Party Invite** | `style: family-invite` | Electro-chic celebration invite (Daft Punk / Pet Shop Boys aesthetic): neon gradients, glassmorphism cards, festival timeline setlist, VIP guestlist pass. |

### Selecting a Theme
1. **Via Markdown Frontmatter (Recommended):**
   ```yaml
   ---
   title: "Pozvánka na shromáždění vlastníků jednotek"
   style: svj-modern
   language: cs
   toc: false
   ---
   ```
2. **Via CLI Argument:**
   ```bash
   ./md-to-report.sh -s svj-community examples/pozvánka-shromáždění-svj.md
   ```

---

## Requirements

- **[Pandoc](https://pandoc.org/)** (v2.x or v3.x)
- Modern web browser (Firefox, Chrome, Edge, Safari) for viewing and printing.
- Optional: `chromium-browser`, `google-chrome`, or `weasyprint` for direct command-line PDF export (`-p` / `--pdf`).

---

## Quick Start

### 1. Basic Compilation

Generate a self-contained, standalone HTML report from any Markdown file:

```bash
# Compile using default forensic styling:
./md-to-report.sh examples/sample-forensic-report.md

# Compile in native print mode with floating print action button:
./md-to-report.sh --print examples/pozvánka-shromáždění-svj.md

# Compile directly to a PDF:
./md-to-report.sh --print -p examples/pozvánka-shromáždění-svj.md -o pozvánka.pdf
```

### 2. View in Browser & Print to PDF

Open the generated HTML in any web browser:

```bash
# Linux
xdg-open report.html

# macOS
open report.html
```

Press **`Ctrl + P`** (or click the floating print button):
- Destination: **Save as PDF**
- Options: Check **"Background graphics"** for colored headers, badges, and cards.
- Paper Size: **A4** (or **Letter**)

---

## CLI Options & Usage

```text
md-to-report.sh [OPTIONS] <input.md> [output.html]
```

| Option | Description | Default |
|---|---|---|
| `-o, --output <file>` | Custom destination path (`.html` or `.pdf`) | `<input>.html` |
| `-t, --title <string>` | Override report title metadata | Extracted from Markdown |
| `-l, --lang <code>` | Set report language (`cs`, `en`) | `en` (or frontmatter) |
| `-s, --style <name/path>`| Theme name (`svj-modern`, `forensic`, etc.) or custom CSS path | `styles/forensic.css` |
| `--print` | Native Print mode (zero-JS, fast & deterministic W3C `@media print`) | Disabled |
| `--paged` | Enable Paged.js W3C CSS Paged Media pagination (simulated A4 sheets on screen) | Disabled |
| `--toc` / `--no-toc` | Toggle executive Table of Contents | Enabled (`--toc`) |
| `--toc-depth <1-6>` | Maximum heading depth shown in TOC | `3` |
| `-N, --number-sections` | Auto-number headings (`1.`, `1.1`, `1.2`) | Off |
| `--highlight-style <name>` | Pandoc syntax highlighting style | `kate` |
| `--embed-resources` | Inlines styles/fonts into a standalone file | Enabled |
| `--no-embed-resources` | Generates lightweight HTML with linked CSS | Disabled |
| `--no-auto-nowrap` | Disables automatic table timestamp unwrapping | Disabled |
| `-p, --pdf` | Compile directly to PDF via Chromium / WeasyPrint | Disabled |
| `--pdf-engine <name>` | Specify explicit PDF engine for Pandoc | Auto-detect |
| `--open` | Open report in default browser after build | Disabled |
| `-v, --verbose` | Show verbose debug output | Disabled |
| `-q, --quiet` | Silence non-error messages | Disabled |
| `-h, --help` | Display comprehensive help screen | - |
| `-V, --version` | Display version information | - |

---

## Markdown Formatting Guide

### 1. YAML Metadata Header
Place this block at the top of your markdown file:

```yaml
---
title: "Digital Forensics Incident Report"
subtitle: "Incident IR-2026-0911A: Host Intrusion Analysis"
author: "Jane Doe"
date: "September 11, 2026"
language: en # or 'cs' for Czech
classification: "CONFIDENTIAL // LAW ENFORCEMENT" # optional override
abstract: |
  Executive summary of the investigation, scope of evidence analyzed,
  and primary conclusions.
---
```

### 2. Localization & Language Support (i18n)

Reports support both **English (`en`)** and **Czech (`cs`)** out of the box. Set the language in frontmatter (`language: cs` or `lang: cs`) or via CLI (`-l cs`).

Localization adapts:
- **Title header badge:** `OFFICIAL FORENSIC REPORT` ↔ `OFICIÁLNÍ FORENZNÍ ZPRÁVA`
- **Examiner label:** `EXAMINER:` ↔ `ZPRACOVAL:`
- **Date label:** `DATE:` ↔ `DATUM:`
- **Running header & footer (Paged.js):** `CONFIDENTIAL...` ↔ `DŮVĚRNÉ`, `Page X` ↔ `Strana X`
- **TOC & Abstract headings:** Automatically localized to `Obsah` and `Abstrakt`
- **Code badges:** `HEX DUMP` ↔ `HEX VÝPIS`, `SYSTEM LOG` ↔ `SYSTÉMOVÝ PROTOKOL`

#### Frontmatter Label Overrides
```yaml
classification: "DUVERNE"       # Overrides footer confidentiality text
report-type: "AUDITNÍ ZPRÁVA"  # Overrides header badge
examiner-label: "Analytik:"    # Overrides author prefix
date-label: "Vystaveno:"       # Overrides date prefix
```

### 3. Forensic Status Badges & Fenced Code Blocks
```html
<span class="badge tlp-amber">TLP:AMBER</span>
<span class="badge badge-critical">SEVERITY: CRITICAL</span>
<span class="badge badge-warning">SUSPICIOUS</span>
<span class="badge badge-success">CLEAN / VERIFIED</span>
```

Syntax highlighting and dark terminal styling are applied automatically:

````markdown
```bash
# Extract evidence hash
sha256sum /opt/forensics/evidence.raw
```

```powershell
Get-WinEvent -FilterHashtable @{LogName='Security';ID=4624}
```
````

### 4. Findings & Evidence Callouts
Use standard blockquotes with strong prefixes or GitHub Alert syntax:

```markdown
> **CRITICAL FINDING**: Unauthorized privilege escalation detected in LSASS process memory.

> **EVIDENCE RECORD**: Hash verified against acquisition log without discrepancies.

> [!WARNING]
> Registry persistence key discovered at `HKLM\Software\Microsoft\Windows\CurrentVersion\Run`.
```

### 5. Unwrapped Timelines & Localized Tables

Forensic timelines and evidence registers require readable, unwrapped timestamps across both screen and print views.

`md-to-report.sh` automatically routes markdown through a built-in Pandoc Lua filter (`filters/table-nowrap.lua`) that:
- Detects timestamp column headers in English (`Timestamp`, `Time`, `Date`, `UTC`) as well as localized headers (`Časová značka`, `Casova znacka`, `Datum`, `Zeitstempel`).
- Inspects table cells for standard date/time patterns (ISO-8601, European dot notation `DD.MM.YYYY HH:MM:SS`, Unix timestamps).
- Prevents line breaks by applying `white-space: nowrap` to header and data cells.

```markdown
| Položka | Časová značka (UTC) | Zdrojový hostitel | Zjištěná aktivita |
|---|---|---|---|
| `LOG-01` | `2026-09-11 02:14:22` | `198.51.100.44` | Iniciační pokus o prolomení perimetru |
| `LOG-02` | `2026-09-11 02:14:58` | `DC-CORP-01` | Spuštění podvrženého procesu PowerShell |
```

---

### 6. Inlined Table of Contents (TOC)

To render a dynamic Table of Contents at an exact location inside the document body (such as under `## Program shromáždění`), use the standard Pandoc Fenced Div or common Markdown directives:

#### Recommended Pandoc Fenced Div:
```markdown
## Program shromáždění

::: {#toc}
:::
```

#### Also Supported:
- `[TOC]` *(Markdown Extra, Typora, Obsidian)*
- `[[_TOC_]]` *(GitLab & GitHub Wiki)*
- `<!-- TOC -->` *(HTML Comment Directive)*

The pre-processing filter automatically populates this placeholder with a clean, anchor-linked `<ol class="agenda-toc">` pointing to all subsequent agenda sections.

---

### 7. Google Docs Numbered Headings Compatibility

When documents are exported from **Google Docs** to Markdown, numbered headings are typically formatted as an ordered list item wrapping a level-3 header:

```markdown
## Detaily jednání

1. ### Zahájení
2. ### Schválení účetní závěrky za rok 2025
3. ### Zhodnocení aktivit v roce 2026
```

#### How `md-style` Handles This:
- The pre-processing filter automatically detects this pattern under `## Detaily jednání` and unrolls the list into clean semantic headings:
  ```html
  <h3 class="agenda-heading" id="zahájení"><span class="agenda-num">1.</span> Zahájení</h3>
  ```
- Any inlined TOC placeholder (`::: {#toc}`, `[TOC]`, etc.) will extract and link these items in sequential order.
- Standard Markdown headings (`### 1. Zahájení` or plain `### Zahájení`) are also supported.

> [!NOTE]
> **Backlog Roadmap:** A planned update will standardize section numbering entirely via CSS counters and native Pandoc AST filters, allowing authors to write pure, standard `### Heading` Markdown without any manual numbers.
