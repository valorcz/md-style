# CSS Layout & Style Development Guide

This document is the definitive technical manual for creating, customizing, and testing layout stylesheets and themes for the `md-style` document toolchain. It is designed to be fully self-contained so that a developer or AI assistant working in a **clean context** can design and implement a new layout from scratch without prior project knowledge.

---

## 1. System Architecture & Processing Pipeline

The `md-style` generator turns Markdown source into standalone, publication-quality HTML and PDF documents using **Pandoc**, **Lua filters**, **custom CSS**, and optionally **Paged.js**.

```text
                ┌───────────────────────────────────┐
                │        Markdown Document          │
                │  (YAML Frontmatter + Markdown)    │
                └─────────────────┬─────────────────┘
                                  │
                                  ▼
                ┌───────────────────────────────────┐
                │          Pandoc Engine            │
                │  Filters: filters/i18n.lua        │
                │           filters/table-nowrap.lua│
                └─────────────────┬─────────────────┘
                                  │
                                  ▼
                ┌───────────────────────────────────┐
                │         Generated HTML5           │
                │  - Inlined base64 fonts (fonts.css│
                │  - Theme CSS (styles/<theme>.css) │
                └─────────────────┬─────────────────┘
                                  │
                 ┌────────────────┴────────────────┐
                 │                                 │
     Standard Screen Mode                --paged Mode (Paged.js)
                 │                                 │
                 ▼                                 ▼
   ┌───────────────────────────┐     ┌───────────────────────────┐
   │ Continuous Responsive Web │     │ Visual Sheets Preview     │
   │  - Clean web reading view │     │  - W3C CSS Paged Media    │
   │  - @media print for Ctrl+P│     │  - Running headers/footers│
   └───────────────────────────┘     │  - Precise A4 page splits │
                                     └─────────────┬─────────────┘
                                                   │
                                                   ▼
                                     ┌───────────────────────────┐
                                     │ Direct PDF Export         │
                                     │  - Chromium / Firefox     │
                                     │  - Exact sheet parity     │
                                     └───────────────────────────┘
```

### Directory Organization

```text
md-style/
├── md-to-report.sh               # CLI compiler & orchestrator
├── filters/
│   ├── i18n.lua                  # Language normalization & AST localization filter
│   └── table-nowrap.lua          # Table timestamp & metric formatting filter
├── styles/
│   ├── fonts.css                 # Embedded base64 web fonts (Roboto Slab, Merriweather, JetBrains Mono)
│   ├── forensic.css              # Reference style: Forensic / Audit Report
│   ├── paged.css                 # Paged.js print sheet framing & running header/footer rules
│   └── <new-theme>.css           # Your custom theme stylesheet(s)
├── templates/
│   └── paged-header.html         # Injected header script for Paged.js initialization
├── vendor/
│   └── paged.polyfill.js         # Vendored offline Paged.js polyfill library
└── docs/
    └── style_development_notes.md# This document
```

---

## 2. Style Switching & CLI Integration

The CLI script `md-to-report.sh` supports selecting themes either by direct file path or by simple theme name:

```bash
# By frontmatter in document.md:
# style: svj-invitation (or school, announcement, family-invite, forensic)
./md-to-report.sh document.md

# Or by CLI argument (searches styles/<name>.css):
./md-to-report.sh -s forensic document.md
./md-to-report.sh -s svj-invitation document.md
./md-to-report.sh -s school document.md
./md-to-report.sh -s announcement document.md
./md-to-report.sh -s family-invite document.md

# In Paged mode (W3C printed sheets preview):
./md-to-report.sh --paged -s school document.md output.html

# Direct PDF export:
./md-to-report.sh --paged --pdf -s announcement document.md output.pdf
```

To add a new theme, create `styles/<theme-name>.css`. It will immediately be accessible via frontmatter `style: <theme-name>` or CLI `-s <theme-name>`.

---

## 3. Theme Concept Archetypes

The following production themes are provided:

| Theme Name | Use Case | Visual Characteristics | Key Components |
| :--- | :--- | :--- | :--- |
| **`forensic`** | Forensic analysis, incident response, technical audit | Dark navy `#0f172a`, high contrast, serif body + slab headings, dark terminal blocks | Dossier header block, TLP badges, cryptographic hash badges, timeline tables |
| **`svj-invitation`** | Building association assembly notice (*SVJ*) | Deep navy `#0f172a`, ocean teal `#2b8a9e`, warm amber `#d97706`, brick red proposals | Address identification block, agenda numbered H3s, proposal callouts, document badge pills |
| **`school`** | Academic papers, school reports, theses, student evaluations | Scholastic navy `#1e3a8a` & burgundy `#881337`, classic serif body, booktabs tables | Student & course dossier grid, grade status badges, definition/theorem callouts, faculty signatures |
| **`announcement`** | Corporate notices, policy memos, internal bulletins | Modern crisp sans-serif, deep indigo `#4338ca`, executive slate | High-impact `MEMORANDUM` eyebrow, `TO/FROM/DATE/SUBJECT` metadata grid, urgency alerts, task checklists |
| **`family-invite`** | Celebrations, birthdays, anniversaries, family gatherings | Warm terracotta `#881337` & golden amber `#d97706`, soft cream background, decorative frame | Centered hero card, event details card (Date/Time/Venue), schedule timeline, RSVP block |

---

## 4. CSS Architecture & Design Token Conventions

All stylesheets in `styles/` must adhere to these conventions to guarantee composability, print fidelity, and maintainability.

### 4.1 CSS Custom Properties (`:root`)

Define all core design tokens at the top of your stylesheet:

```css
:root {
  /* Typography */
  --font-heading: 'Roboto Slab', Georgia, serif;
  --font-body: 'Merriweather', Georgia, serif;
  --font-code: 'JetBrains Mono', monospace;

  /* Color Palette */
  --color-primary: #0f172a;
  --color-secondary: #334155;
  --color-accent: #2563eb;
  --color-surface: #ffffff;
  --color-surface-subtle: #f8fafc;
  --color-border: #e2e8f0;
  --color-text: #1e293b;
  --color-text-muted: #64748b;

  /* Layout Spacing */
  --content-width: 860px;
  --line-height-body: 1.65;
  --line-height-heading: 1.25;

  /* Internationalized Content Tokens (English defaults) */
  --i18n-header-badge: "OFFICIAL REPORT";
  --i18n-author-label: "AUTHOR:";
  --i18n-date-label: "DATE:";
  --i18n-classification: "CONFIDENTIAL";
}
```

### 4.2 Internationalization (i18n) Rules

> [!IMPORTANT]
> **Never hardcode user-visible strings directly into CSS `content: "..."` rules.**
> All static generated text (labels, headers, badges) must use CSS tokens with language selectors.

#### CSS Token Pattern:
```css
/* 1. English (Default on :root) */
:root {
  --i18n-header-badge: "OFFICIAL REPORT";
  --i18n-author-label: "AUTHOR:";
  --i18n-date-label: "DATE:";
  --i18n-classification: "CONFIDENTIAL";
}

/* 2. Czech Localization */
:root:lang(cs),
[lang="cs"] {
  --i18n-header-badge: "OFICIÁLNÍ ZPRÁVA";
  --i18n-author-label: "ZPRACOVAL:";
  --i18n-date-label: "DATUM:";
  --i18n-classification: "DŮVĚRNÉ";
}

/* 3. Usage in CSS */
.report-badge::before {
  content: var(--custom-badge-override, var(--i18n-header-badge));
}
.author-label::before {
  content: var(--custom-examiner-override, var(--i18n-author-label));
}
```

#### How Frontmatter Controls Language:
Pandoc passes the document language to the HTML root (`<html lang="cs">`). The filter `filters/i18n.lua` normalizes frontmatter:
- `language: cs` or `lang: cs` activates `:root:lang(cs)`.
- Frontmatter overrides (e.g. `classification: "INTERNÍ"`, `examiner-label: "VYŠETŘOVATEL:"`) inject custom CSS properties directly into the document root, superseding the localized defaults.

---

## 5. Paged Media & Paged.js (Critical Layout Knowledge)

When compiling with `--paged`, Paged.js transforms the continuous HTML DOM into discrete printed pages inside the browser. This allows users to preview actual sheets on screen and print without layout surprises.

### 5.1 The Firefox / Gecko Table Fragmentation Bug & The Fix

> [!WARNING]
> **Understanding Gecko's Multi-Column Engine:**
> Paged.js internally assigns `.pagedjs_page_content { column-width: [width]px; }` to measure layout overflow using the browser's CSS multi-column engine.
>
> In **Mozilla Firefox (Gecko)**, an HTML `<table>` inside a CSS multi-column container **refuses to fragment if there is any preceding content in that column** (even a 20px heading or paragraph). Gecko considers the column "too full" and pushes the entire table to the next column. Heading orphan protection (`break-after: avoid`) then drags the preceding heading onto the next page as well, leaving massive blank gaps (700px+ empty).

#### The Mandatory Fix in `styles/paged.css`:
```css
.pagedjs_page_content {
  /* Forces vertical block layout; bypasses Gecko multi-column table bug */
  column-width: auto !important;
  columns: auto !important;

  /* Print typography calibration */
  font-size: 9.5pt !important;
  line-height: 1.55 !important;
  color: #1e293b !important;
}
```

By resetting `column-width: auto !important`, Gecko processes content vertically. Paged.js's vertical overflow detector (`top >= vEnd`) catches the exact row exceeding the page bottom, cleanly fragments the table across pages, and avoids false orphan breaks.

### 5.2 Table Pagination & Fragmentation Rules

To ensure tables split cleanly across page cuts without severed rows or missing headers:

```css
table {
  width: 100% !important;
  max-width: 100% !important;
  border-collapse: collapse !important;
  border-radius: 0 !important;
  box-shadow: none !important;
  overflow: visible !important;       /* Mandatory: overflow:hidden forbids page splitting */
  page-break-inside: auto !important;
  break-inside: auto !important;
  margin: 1em 0 1.2em !important;
  font-size: 8.5pt !important;
}

tbody {
  page-break-inside: auto !important;
  break-inside: auto !important;
}

thead {
  display: table-header-group !important; /* Repeats table header across split pages */
  break-inside: avoid !important;
  page-break-inside: avoid !important;
  break-after: avoid !important;
  page-break-after: avoid !important;
}

tr {
  break-inside: avoid !important;     /* Prevents slicing a single row across page edges */
  page-break-inside: avoid !important;
}

th, td {
  overflow-wrap: break-word !important;
}
```

### 5.3 Heading Orphan & Widow Protection

Headings must never be isolated at the very bottom of a page:

```css
h1, h2, h3, h4, h5, h6 {
  break-after: avoid !important;
  page-break-after: avoid !important;
}

/* Compact heading margins in print mode prevent pushing following content onto blank pages */
.pagedjs_page_content h1 { margin-top: 1.4em !important; margin-bottom: 0.4em !important; }
.pagedjs_page_content h2 { margin-top: 1.2em !important; margin-bottom: 0.35em !important; }
.pagedjs_page_content h3 { margin-top: 1.0em !important; margin-bottom: 0.3em !important; }
```

### 5.4 Running Headers & Footers (Paged Media)

Running headers and footers are declared using W3C CSS Paged Media `@page` margin boxes inside `styles/paged.css`:

```css
@page {
  size: A4 portrait;
  margin: 18mm 14mm 18mm 14mm;

  @top-left {
    content: var(--custom-report-type-override, var(--i18n-header-badge));
    font-size: 7.5pt;
    font-weight: 700;
    color: #64748b;
  }

  @top-right {
    content: string(heading-title);
    font-size: 7.5pt;
    color: #64748b;
  }

  @bottom-left {
    content: var(--custom-classification-override, var(--i18n-classification));
    font-size: 7.5pt;
    font-weight: 700;
    color: #dc2626;
  }

  @bottom-right {
    content: var(--page-footer-right, var(--i18n-page-prefix, "Page ") counter(page) " / " counter(pages));
    font-size: 7.5pt;
    color: #64748b;
  }
}

/* Suppress all running headers/footers on cover/title/notice page */
@page:first {
  @top-left { content: none !important; }
  @top-right { content: none !important; }
  @bottom-left { content: none !important; }
  @bottom-right { content: none !important; }
}

.pagedjs_first_page .pagedjs_margin-box {
  visibility: hidden !important;
  display: none !important;
}

/* Force strict page break before a specific section */
#detaily-jednání,
.page-break-before {
  break-before: page !important;
  page-break-before: always !important;
}
```

---

## 6. Step-by-Step: Developing a New Style in a Clean Context

When you or an AI assistant start in a clean context to develop a new style, follow this exact procedure:

### Step 1: Create a Representative Markdown Test File
Create `examples/<theme>-sample.md` demonstrating all elements relevant to that style (headers, callouts, tables, lists, quotes, metadata).

```yaml
---
title: "Sample School Report: Physics Laboratory"
subtitle: "Measurement of Gravitational Acceleration"
author: "Alex Morgan"
date: "October 14, 2026"
language: en
abstract: |
  Brief synopsis of the lab experiment and methodology used.
---

# 1. Introduction
...
```

### Step 2: Create `styles/<theme>.css`
1. Define CSS custom properties (`:root` and `:root:lang(cs)`).
2. Style the header block (`#title-block-header`, `.title`, `.subtitle`, `.author`, `.date`).
3. Style body typography (`p`, `ul`, `ol`, `blockquote`).
4. Style structural elements (`h1`, `h2`, `h3`, `hr`).
5. Style code and data blocks (`pre`, `code`, `table`).
6. Add theme-specific callout boxes (`.callout`, `.warning`, `.note`).
7. Add `@media print` rules ensuring colors are toner-friendly and background graphics render cleanly.

### Step 3: Test Standard Compilation
```bash
./md-to-report.sh -s <theme> examples/<theme>-sample.md output.html
```
Verify the continuous HTML view renders properly in your browser.

### Step 4: Test Paged Compilation
```bash
./md-to-report.sh --paged -s <theme> examples/<theme>-sample.md output-paged.html
```
Verify that page numbers, headers, and footers render properly across sheets.

### Step 5: Execute Dual-Browser Headless Verification
Always verify pagination across both **Gecko (Firefox)** and **Blink (Chromium)** using the automated test harness (see Section 7).

---

## 7. Headless Automated Verification Harness

Use this standalone Python test script to verify that a compiled `--paged` HTML report lays out identically in both Firefox and Chromium without manual inspection.

Save as `test_layout.py`:

```python
#!/usr/bin/env python3
import http.server
import socketserver
import subprocess
import threading
import json
import time
import os
import sys

PORT = 8979
HTML_FILE = sys.argv[1] if len(sys.argv) > 1 else "output-paged.html"

results = {}

class Handler(http.server.SimpleHTTPRequestHandler):
    def do_POST(self):
        length = int(self.headers['Content-Length'])
        data = json.loads(self.rfile.read(length).decode('utf-8'))
        results[data['browser']] = data
        self.send_response(200)
        self.end_headers()

def run_test(browser_name, cmd):
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(('127.0.0.1', PORT), Handler)
    server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    server_thread.start()

    with open(HTML_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    reporter_script = f"""
    <script>
    window.addEventListener('DOMContentLoaded', () => {{
        let attempts = 0;
        const timer = setInterval(() => {{
            attempts++;
            const pages = document.querySelectorAll('.pagedjs_page');
            const loading = document.querySelector('.pagedjs_pages')?.classList.contains('pagedjs_loading');
            if ((pages.length > 0 && !loading) || attempts > 60) {{
                clearInterval(timer);
                setTimeout(sendReport, 1000);
            }}
        }}, 200);

        function sendReport() {{
            const pages = Array.from(document.querySelectorAll('.pagedjs_page')).map((p, idx) => {{
                const contentEl = p.querySelector('.pagedjs_page_content');
                const root = (contentEl && contentEl.children.length === 1 && contentEl.children[0].tagName === 'DIV') 
                             ? contentEl.children[0] : contentEl;
                const children = root ? Array.from(root.children).map(c => c.tagName) : [];
                return {{ pageNumber: idx + 1, elements: children }};
            }});

            fetch('http://127.0.0.1:{PORT}', {{
                method: 'POST',
                headers: {{'Content-Type': 'application/json'}},
                body: JSON.stringify({{ browser: '{browser_name}', totalPages: pages.length, pages: pages }})
            }});
        }}
    }});
    </script>
    """
    temp_path = f"/tmp/verify_{browser_name}.html"
    with open(temp_path, 'w', encoding='utf-8') as f:
        f.write(content.replace('</body>', reporter_script + '</body>'))

    proc = subprocess.Popen(cmd + [f"http://127.0.0.1:{PORT}/verify_{browser_name}.html"], cwd="/tmp")
    start_time = time.time()
    while browser_name not in results and (time.time() - start_time) < 15:
        time.sleep(0.4)

    proc.terminate()
    try:
        proc.wait(timeout=2)
    except:
        proc.kill()
    httpd.shutdown()
    if os.path.exists(temp_path):
        os.remove(temp_path)

if __name__ == '__main__':
    print(f"Verifying {HTML_FILE}...")
    run_test('Firefox', ['firefox', '--headless'])
    run_test('Chromium', ['chromium-browser', '--headless', '--disable-gpu', '--no-sandbox'])

    print("\n--- RESULTS ---")
    for b in ['Firefox', 'Chromium']:
        if b in results:
            print(f"[{b}] Total Pages: {results[b]['totalPages']}")
            for p in results[b]['pages']:
                print(f"  Page {p['pageNumber']}: {', '.join(p['elements'][:6])}")
        else:
            print(f"[{b}] FAILED to record layout.")
```

Run it via:
```bash
python3 test_layout.py output-paged.html
```

---

## 8. Quality Checklist for New Themes

Before finalizing any new layout or stylesheet, verify each item:

- [ ] **Design Tokens**: All colors, fonts, and dimensions use CSS variables (`:root`).
- [ ] **Dual-Language i18n**: No hardcoded strings in CSS pseudo-elements; tokens defined for `:root` (English) and `:root:lang(cs)` (Czech).
- [ ] **Responsive Reading View**: In standard screen mode, content wraps cleanly, max-width is constrained (`800–900px`), and side margins are responsive.
- [ ] **Paged Sheet View**: Compiles cleanly with `--paged`; pages display drop-shadow boundaries in screen preview.
- [ ] **Engine Parity**: Firefox and Chromium produce identical page counts and element distributions without gaps.
- [ ] **Table Integrity**: Tables split across pages without severed rows; headers repeat via `thead { display: table-header-group }`.
- [ ] **Orphan Protection**: Headings have `break-after: avoid; page-break-after: avoid;`.
- [ ] **Toner / Ink Efficiency**: Print mode converts dark blocks to light/outlined containers to save toner.
