# Markdown Forensic Report Styler (`md-style`)

> A robust, modern document generation toolchain for transforming Markdown into publication-ready **Digital Forensics, Incident Response (DFIR), and Technical Audit Reports** using Pandoc.

---

## Highlights

- **Authoritative Typography**:
  - Headings: **Roboto Slab** (weights 400, 600, 700) for structured legal/technical authority.
  - Body Text: **Merriweather** (weights 300, 400, 700) for high legibility across long investigative narratives.
  - Code & Monospace: **JetBrains Mono** with ligatures enabled for clear distinction between zero `0` and capital `O`, lowercase `l` and number `1`.
- **Specialized Code Block & Monospace Highlighting**:
  - Dark terminal aesthetic with macOS window indicator controls.
  - Automatic language badge indicator (e.g. `BASH`, `PYTHON`, `POWERSHELL`, `JSON`, `YARA`, `HEX DUMP`).
  - Resilient inline code tokens with auto-wrap support for cryptographic hashes (`SHA-256`, `MD5`), IP addresses, registry paths, and memory offsets without breaking table boundaries.
  - High-contrast syntax highlighting palette with line-numbering support.
- **Forensic Case Artifacts & Callouts**:
  - Executive case dossier header with examiner metadata, case numbers, and abstracts.
  - Traffic Light Protocol (`TLP:AMBER`, `TLP:RED`, etc.) and severity status badges.
  - Callout containers for `CRITICAL FINDINGS`, `WARNINGS`, `EVIDENCE ACQUISITION`, and `CHAIN OF CUSTODY`.
  - Professional tables tailored for event timelines, evidence registries, and hash ledgers.
- **Print & PDF Optimization (`@media print`)**:
  - Tuned `@page` setup (A4 / Letter margins, orphan/widow protection).
  - Page-break controls preventing split tables, code blocks, or severed headings.
  - **Ink-friendly print mode**: automatically converts code containers to a clean light background for paper clarity and toner conservation.
- **Robust Tooling**:
  - Modernized CLI script with comprehensive error handling, input validation, help screens, and flags.

---

## Directory Structure

```text
md-style/
├── md-to-report.sh                 # Primary CLI report generator (robust, error-handled)
├── md-to-html.sh                   # Compatibility wrapper forwarding to md-to-report.sh
├── filters/
│   └── table-nowrap.lua            # Lua filter for unwrapped timestamps & localized headers
├── styles/
│   └── forensic.css                # Forensic report stylesheet with custom fonts & print rules
├── examples/
│   ├── sample-forensic-report.md   # Comprehensive reference report demonstrating all features
│   └── sample-forensic-report.html # Pre-compiled standalone output showcase
├── deprecated/                     # Archived legacy prototype files
│   ├── branding.css
│   ├── confluence-branding.css
│   ├── markdown-pdf.css
│   ├── md-to-html.sh.prototype
│   ├── md-to-ipynb.sh
│   └── pandoc.css
└── README.md                       # Documentation
```

---

## Requirements

- **[Pandoc](https://pandoc.org/)** (v2.x or v3.x)
- Modern web browser (Firefox, Chrome, Edge, Safari) for viewing and printing.

---

## Quick Start

### 1. Basic Compilation

Generate a self-contained, standalone HTML report from any Markdown file:

```bash
./md-to-report.sh examples/sample-forensic-report.md
```

This compiles `examples/sample-forensic-report.html` with all styles and fonts embedded.

### 2. View in Browser & Print to PDF

Open the generated HTML in any web browser:

```bash
# Linux
xdg-open examples/sample-forensic-report.html

# macOS
open examples/sample-forensic-report.html
```

Press **`Ctrl + P`** (or **`Cmd + P`** on macOS):
- Destination: **Save as PDF**
- Options: Check **"Background graphics"** for colored headers, badges, and table highlights.
- Paper Size: **A4** or **Letter**

---

## CLI Options & Usage

```text
md-to-report.sh [OPTIONS] <input.md> [output.html]
```

| Option | Description | Default |
|---|---|---|
| `-o, --output <file>` | Custom destination path (`.html` or `.pdf`) | `<input>.html` |
| `-t, --title <string>` | Override report title metadata | Extracted from Markdown |
| `-s, --style <file>` | Path to custom CSS stylesheet | `styles/forensic.css` |
| `--toc` / `--no-toc` | Toggle executive Table of Contents | Enabled (`--toc`) |
| `--toc-depth <1-6>` | Maximum heading depth shown in TOC | `3` |
| `-N, --number-sections` | Auto-number headings (`1.`, `1.1`, `1.2`) | Off |
| `--highlight-style <name>` | Pandoc syntax highlighting style | `kate` |
| `--embed-resources` | Inlines styles/fonts into a standalone file | Enabled |
| `--no-embed-resources` | Generates lightweight HTML with linked CSS | Disabled |
| `--no-auto-nowrap` | Disables automatic table timestamp unwrapping | Disabled |
| `-p, --pdf` | Compile directly to PDF via available engines | Disabled |
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
author: "Examiner: Jane Doe, GCFA | Forensic Analysis Unit"
date: "September 11, 2026"
abstract: |
  Executive summary of the investigation, scope of evidence analyzed,
  and primary conclusions.
---
```

### 2. Forensic Status Badges
```html
<span class="badge tlp-amber">TLP:AMBER</span>
<span class="badge badge-critical">SEVERITY: CRITICAL</span>
<span class="badge badge-warning">SUSPICIOUS</span>
<span class="badge badge-success">CLEAN / VERIFIED</span>
```

### 3. Fenced Code Blocks with Language Badges
Syntax highlighting and terminal styling are applied automatically:

````markdown
```bash
# Extract evidence hash
sha256sum /opt/forensics/evidence.raw
```

```powershell
Get-WinEvent -FilterHashtable @{LogName='Security';ID=4624}
```

```python
def parse_artifact(stream):
    return hashlib.sha256(stream.read()).hexdigest()
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

#### Automatic Detection (Default)
`md-to-report.sh` automatically routes markdown through a built-in Pandoc Lua filter (`filters/table-nowrap.lua`) that:
- Detects timestamp column headers in English (`Timestamp`, `Time`, `Date`, `Acquisition Time`, `UTC`) as well as **localized headers** (Czech/Slovak `Časová značka`, `Casova znacka`, `Datum`, German `Zeitstempel`, etc.).
- Inspects table cells for standard date/time patterns (ISO-8601 `YYYY-MM-DD HH:MM:SS`, European dot notation `DD.MM.YYYY HH:MM:SS`, Unix timestamps).
- Prevents line breaks by applying `white-space: nowrap` to header and data cells.

```markdown
| Položka | Časová značka (UTC) | Zdrojový hostitel | Zjištěná aktivita |
|---|---|---|---|
| `LOG-01` | `2026-09-11 02:14:22` | `198.51.100.44` | Iniciační pokus o prolomení perimetru |
| `LOG-02` | `2026-09-11 02:14:58` | `DC-CORP-01` | Spuštění podvrženého procesu PowerShell |
```

#### Manual Authoring Methods
If you prefer explicit control in base Markdown:
1. **Non-breaking space**: Use `&nbsp;` between date and time:
   `2026-09-11&nbsp;02:14:22`
2. **Pandoc Bracketed Spans**:
   `[`2026-09-11 02:14:22`]{.nowrap}`
3. **Timeline Div Containers**:
   Wrap any table in `::: {.table-timeline}` to keep the first column unwrapped and fitted.

---

## Deprecated Prototype Archive

All original prototype files have been organized into the [`deprecated/`](file:///home/valor/Devel/personal/md-style/deprecated) directory for historical reference:
- `deprecated/branding.css`
- `deprecated/confluence-branding.css`
- `deprecated/markdown-pdf.css`
- `deprecated/pandoc.css`
- `deprecated/md-to-ipynb.sh`
- `deprecated/md-to-html.sh.prototype`
