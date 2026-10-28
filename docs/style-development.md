# Style & Layout Development Guide

This document is the technical manual for creating, styling, and testing layout stylesheets and themes for the `md-style` document toolchain. It is designed so that a developer or designer working in a **clean context** can design and implement a new theme from scratch.

---

## 1. Theme Concept Archetypes

The toolchain provides production themes categorized into domain families:

| Theme Name | Family | Visual Characteristics | Key Components |
| :--- | :--- | :--- | :--- |
| **`forensic/cyber`** (`forensic-cyber`) | `forensic` | Dark HUD `#090d16`, cyan/emerald glowing accents, monospaced data, slide-over inspector drawer | Cyber indicator pills, timeline pulse, interactive HUD filters, dark code blocks |
| **`forensic/dossier`** (`forensic`) | `forensic` | Navy `#0f172a`, serif body, high contrast, formal legal evidence dossier | TLP badges, cryptographic hash cards, chain-of-custody tables, investigator signatures |
| **`svj/modern`** (`svj-modern`) | `svj` | Clean corporate navy `#0f172a` & teal `#2b8a9e`, modern sans-serif | Assembly agenda callouts, quorum indicators, resolution proposal cards |
| **`svj/ballot`** (`svj-ballot`) | `svj` | High-contrast black/white print layout | Per-proposal voting ballot boxes (PRO / PROTI / ZDRŽEL SE), owner signature blocks |
| **`school`** | Standalone | Scholastic navy `#1e3a8a` & burgundy `#881337`, classic serif typography | Student/course dossier grid, grade status badges, definition/theorem callouts |
| **`announcement`** | Standalone | Modern corporate indigo `#4338ca`, executive slate | `MEMORANDUM` header eyebrow, `TO/FROM/DATE/SUBJECT` metadata grid, urgency alert banners |
| **`family-invite`** | Standalone | Warm terracotta `#881337` & golden amber `#d97706`, decorative border framing | Centered hero card, venue/time details card, event schedule, RSVP block |

---

## 2. CSS Architecture & Design Token Conventions

All stylesheets must follow strict design token conventions to guarantee composability, print fidelity, and internationalization compatibility.

### 2.1 CSS Custom Properties (`:root`)
Declare all color palettes, typography stacks, and layout constraints at the top of your stylesheet:

```css
:root {
  /* Typography Stacks */
  --font-heading: 'Roboto Slab', Georgia, serif;
  --font-body: 'Merriweather', Georgia, serif;
  --font-code: 'JetBrains Mono', 'Fira Code', monospace;

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
}
```

### 2.2 Consuming Localized Strings
> [!IMPORTANT]
> **Never hardcode user-visible strings directly into CSS `content: "..."` rules.**
> Do not use `:root:lang(cs)` or `[lang="cs"]` selectors in stylesheets.

All static generated text (labels, headers, badges, footers) must consume CSS variables injected by the 3-tier localization engine ([Localization Guide](localization.md)):

```css
/* Good: Uses localized token with fallback */
.report-badge::before {
  content: var(--custom-badge-override, var(--i18n-header-badge, "OFFICIAL REPORT"));
}

.examiner-label::before {
  content: var(--custom-examiner-override, var(--i18n-author-label, "INVESTIGATOR:"));
}

/* Page footer in paged mode */
@page {
  @bottom-right {
    content: var(--page-footer-right, var(--i18n-page-prefix, "Page ") counter(page) var(--i18n-page-of, " of ") counter(pages));
  }
}
```

---

## 3. Paged Media & Paged.js (Print Fidelity)

When compiling with `--paged` or `--pdf`, [Paged.js](https://pagedjs.org/) fragments the continuous HTML DOM into discrete printed pages inside the browser.

### 3.1 The Gecko / Firefox Multi-Column Table Bug & Fix
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

### 3.2 Table Pagination & Fragmentation Rules
To ensure tables split cleanly across page cuts without severed rows or missing headers:

```css
table {
  width: 100% !important;
  max-width: 100% !important;
  border-collapse: collapse !important;
  overflow: visible !important;           /* Mandatory: overflow:hidden forbids page splitting */
  page-break-inside: auto !important;
  break-inside: auto !important;
  margin: 1em 0 1.2em !important;
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
  break-inside: avoid !important;         /* Prevents slicing a single row across page edges */
  page-break-inside: avoid !important;
}

th, td {
  overflow-wrap: break-word !important;
}
```

### 3.3 Heading Orphan & Widow Protection
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

### 3.4 Running Headers & Footers
Running headers and footers are declared using W3C CSS Paged Media `@page` margin boxes:

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
    content: var(--custom-classification-override, var(--i18n-confidential-label));
    font-size: 7.5pt;
    font-weight: 700;
    color: #dc2626;
  }

  @bottom-right {
    content: var(--page-footer-right, var(--i18n-page-prefix, "Page ") counter(page) var(--i18n-page-of, " / ") counter(pages));
    font-size: 7.5pt;
    color: #64748b;
  }
}

/* Suppress all running headers/footers on first / title page */
@page:first {
  @top-left { content: none !important; }
  @top-right { content: none !important; }
  @bottom-left { content: none !important; }
  @bottom-right { content: none !important; }
}
```

---

## 4. Step-by-Step: Developing a New Style in a Clean Context

When you or an AI assistant start in a clean context to develop a new style, follow this exact workflow:

### Step 1: Create a Representative Markdown Test File
Create `examples/<theme>-sample.md` demonstrating all elements relevant to that style (headers, callouts, tables, lists, quotes, metadata).

### Step 2: Create Theme Stylesheet & Localization Catalogs
1. Create `styles/<family>/<theme>.css` (or `styles/<theme>.css`).
2. Add style-specific dictionary tokens in `styles/i18n/<theme>/en.json` and `styles/i18n/<theme>/cs.json`.
3. Style the header block (`#title-block-header`, `.title`, `.subtitle`, `.author`, `.date`).
4. Style body typography (`p`, `ul`, `ol`, `blockquote`).
5. Style code blocks and tables (`pre`, `code`, `table`).
6. Add theme-specific callout boxes (`.callout`, `.warning`, `.note`).
7. Add `@media print` rules ensuring colors are toner-friendly.

### Step 3: Test Standard Compilation
```bash
uv run md-to-report examples/<theme>-sample.md -s <theme> -o output/test.html
```

### Step 4: Test Paged Compilation
```bash
uv run md-to-report examples/<theme>-sample.md -s <theme> --paged -o output/test-paged.html
```

### Step 5: Execute Dual-Browser Layout Verification
Verify pagination across both **Gecko (Firefox)** and **Blink (Chromium)** using the automated harness (see Section 5).

---

## 5. Headless Automated Verification Harness

Use this standalone script to verify that a compiled `--paged` HTML report lays out identically in both Firefox and Chromium without manual inspection.

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

---

## 6. Quality Checklist for New Themes

Before committing any new layout or stylesheet:
- [ ] **Design Tokens**: All colors, fonts, and dimensions use CSS variables (`:root`).
- [ ] **No Hardcoded Strings**: No static text in CSS `content: "..."` rules; uses `var(--i18n-...)`.
- [ ] **No CSS `:root:lang()`**: Localization is driven exclusively via JSON catalogs.
- [ ] **Responsive Reading View**: In standard screen mode, content wraps cleanly, max-width is constrained (`800–900px`).
- [ ] **Paged Sheet View**: Compiles cleanly with `--paged`; pages display drop-shadow boundaries in screen preview.
- [ ] **Engine Parity**: Firefox and Chromium produce identical page counts and element distributions.
- [ ] **Table Integrity**: Tables split across pages without severed rows; headers repeat via `thead { display: table-header-group }`.
- [ ] **Orphan Protection**: Headings have `break-after: avoid; page-break-after: avoid;`.
- [ ] **Toner Efficiency**: Print mode converts dark blocks to light/outlined containers to save toner.
