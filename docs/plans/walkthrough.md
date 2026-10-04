# Walkthrough: Restoring Pure PDF Generation & Native GFM Callouts

---

## 1. Summary of Changes

In this iteration, we addressed the core issues identified in the architectural review:

1. **Fixed PDF Engine Auto-Routing & Eliminated `pdflatex` Dependency**:
   - **Root Cause**: When users provided an output path ending in `.pdf` without passing `-p / --pdf`, `generate_pdf` defaulted to `False`. Pandoc was invoked with `-o <name>.pdf`, triggering its default fallback to `pdflatex`.
   - **Resolution**: Both [`core/cli.py`](file:///home/valor/Devel/personal/md-style/core/cli.py) and [`core/engine.py`](file:///home/valor/Devel/personal/md-style/core/engine.py) now automatically detect `.pdf` suffixes on the target output and set `generate_pdf = True`.
   - **Embedded Resources**: Enabled `--embed-resources` for intermediate HTML during PDF compilation so headless Chromium receives fully inlined fonts, CSS, and SVGs.
   - **Zero LaTeX Requirement**: PDF compilation now routes exclusively through headless Chromium (or WeasyPrint).

2. **Migrated to Pandoc Native GFM (`gfm+smart+fenced_divs+bracketed_spans`)**:
   - Switched Pandoc input format to leverage native GitHub alert callouts (`> [!NOTE]`, `> [!TIP]`, `> [!IMPORTANT]`, `> [!WARNING]`, `> [!CAUTION]`), footnotes (`[^1]`), task lists (`- [x]`), fenced divs (`::: {.class}`), and bracketed spans (`[text]{.class}`).
   - **Eliminated `filters/callouts.lua`**: Removed 140 lines of custom Lua AST blockquote parsing, reducing pipeline complexity and AST race conditions.

3. **Pure CSS Vector Callout Icons & Strict Print Isolation**:
   - Updated [`styles/base.css`](file:///home/valor/Devel/personal/md-style/styles/base.css) with pure CSS vector icons via CSS `mask` and inline data-URIs matching `currentColor`.
   - Enforced `@media print` rules in `base.css` and `print.css` to strictly hide screen HUD elements (`.cyber-drawer`, `.drawer-backdrop`, `.hud-bar`, `.theme-toggle`, `.reading-progress`, `#report-toc-hud`) to protect paper pagination and page breaks.

---

## 2. Verification & Automated Tests

All tests passed successfully:

### Test 1: SVJ Meeting Notice to PDF
```bash
uv run md-to-report examples/pozvánka-shromáždění-svj.md -s svj/modern -o output/pozvanka.pdf
```
- **Result**: `output/pozvanka.pdf: PDF document, version 1.4, 5 page(s) (435 KB)` generated via headless Chromium in 7.47s with zero errors.

### Test 2: School Progress Report to PDF
```bash
uv run md-to-report examples/school-report-sample.md -s school -o output/school.pdf
```
- **Result**: `output/school.pdf: PDF document, version 1.4, 2 page(s) (135 KB)` generated in 7.00s.

### Test 3: Forensic Dossier with Mermaid Diagrams to PDF
```bash
uv run md-to-report examples/sample-forensic-report.md -s forensic/dossier -o output/forensic.pdf
```
- **Result**: Pre-rendered 2 Mermaid diagrams to SVG (0.47s), compiled to `output/forensic.pdf: PDF document, version 1.4, 8 page(s) (476 KB)` in 12.45s.

### Test 4: GFM Features (Callouts, Footnotes, Checklists) Test
```bash
uv run md-to-report tests/test-gfm-features.md -o output/test-gfm.html
uv run md-to-report tests/test-gfm-features.md -o output/test-gfm.pdf
```
- **HTML Output**: Native `<div class="note"><div class="title"><p>Note</p></div>...</div>`, `<div class="tip">`, `<div class="important">`, `<div class="warning">`, `<div class="caution">`, and native `<section id="footnotes">`.
- **PDF Output**: Clean 2-page publication PDF with vector callout icons, footnotes, and checkboxes.

---

## 3. Forensic Metadata & Header Block Fix

- **Root Cause**: `core/engine.py` was prepending `<style>{css_custom_props}</style>` directly to the top of `processed_md`. When input does not start with `---` at line 1, Pandoc fails to parse the YAML metadata block, treating it as regular Markdown body text (`<hr /><h2>title: ...</h2>`) and corrupting the TOC.
- **Resolution**:
  - Routed `css_custom_props` to a temporary HTML snippet passed via `--include-in-header` instead of mutating the raw Markdown stream.
  - Adjusted examiner label in [`styles/i18n/forensic/en.json`](file:///home/valor/Devel/personal/md-style/styles/i18n/forensic/en.json) to `"EXAMINER:"` to fit title block columns.
  - Verified title block, author metadata, abstract, and TOC compilation.

---

## 4. Forensic Word-Wrapping & CVE Population Fixes

### 1. Forensic Word-Wrapping Enforcement
- **Root Cause**:
  - In [`styles/forensic.css`](file:///home/valor/Devel/personal/md-style/styles/forensic.css), `code, kbd, samp` had `white-space: pre-wrap; overflow-wrap: break-word;`, causing inline code tokens, paths, and commands to wrap across lines.
  - In [`styles/forensic-cyber.css`](file:///home/valor/Devel/personal/md-style/styles/forensic-cyber.css), `code.ioc, .ioc, .cyber-ioc` was grouped with `code.hash` and had `word-break: break-all;`, forcing IP addresses, CVEs, and Event IDs to split arbitrarily mid-character.
  - In [`core/engine.py`](file:///home/valor/Devel/personal/md-style/core/engine.py), `filters/table-nowrap.lua` was omitted from the filter chain when `auto_nowrap` was active.
- **Resolution**:
  - In both [`styles/forensic.css`](file:///home/valor/Devel/personal/md-style/styles/forensic.css) and [`styles/forensic-cyber.css`](file:///home/valor/Devel/personal/md-style/styles/forensic-cyber.css) (and their respective `@media print` blocks):
    - Inline code (`code:not(pre code)`), keyboard keys (`kbd`), samples (`samp`), IoCs (`.ioc`, `.cyber-ioc`), MITRE pills (`.mitre-pill`), event IDs (`.eid`, `.eventid-pill`), EVTX names (`.evtx-pill`), custom knowledge pills (`.custom-pill`), and table timestamp cells (`td.nowrap`, `th.nowrap`) are strictly set to:
      `white-space: nowrap !important; word-break: keep-all !important; overflow-wrap: normal !important;`
    - Hashes and break-all tokens (`code.hash`, `.hash`, `code.break-all`, `.break-all`, `.drawer-val-box`) are explicitly allowed to wrap anywhere to prevent table blowout:
      `white-space: normal !important; word-break: break-all !important; overflow-wrap: anywhere !important;`
  - Re-attached `filters/table-nowrap.lua` in `core/engine.py` when `self.config.auto_nowrap` is enabled on styles without dedicated filters.

### 2. CVE Population & CIRCL JSON 5 Parser
- **Root Cause**:
  - CIRCL Vulnerability Lookup upgraded to CVE JSON 5.x (`containers.cna` structure).
  - [`core/providers/cve_provider.py`](file:///home/valor/Devel/personal/md-style/core/providers/cve_provider.py) searched for top-level `id`, `summary`, and `cvss`, returning `None` and caching empty records (`"summary": "No detailed synopsis available.", "score": null, "affected": []`) into [`data/cache/cve.json`](file:///home/valor/Devel/personal/md-style/data/cache/cve.json).
  - `CVE-2026-3184` is a hypothetical 2026 incident zero-day in `sample-forensic-cyber.md` that was not pre-populated in the cache.
- **Resolution**:
  - Rebuilt `CveProvider.fetch()` to parse CVE JSON 5.x `containers.cna`:
    - English/primary description extraction.
    - CVSS metric extraction (`cvssV4_0`, `cvssV3_1`, `cvssV3_0`, `cvssV2_0`) for `baseScore` and `baseSeverity`.
    - Affected vendor/product list extraction.
    - Seamless fallback to legacy CVE 4.x fields.
  - Enriched [`data/cache/cve.json`](file:///home/valor/Devel/personal/md-style/data/cache/cve.json) with rich data:
    - `CVE-2024-21762`: Fortinet FortiOS / FortiProxy Out-of-Bounds Write (CVSS 9.6 Critical).
    - `CVE-2026-3184`: Perimeter VPN Remote Buffer Overflow (Zero-Day, CVSS 9.8 Critical).
  - Verified in `output/cyber.html` that clicking CVE pills immediately displays complete descriptions, CVSS scores, CRITICAL badges, and affected product lists.

  1. `core/engine.py` now writes CSS custom properties to a temporary HTML header file and attaches it via `--include-in-header`, keeping the Markdown source cleanly beginning with `---`.
  2. Pandoc now correctly populates `#title-block-header` with `title`, `subtitle`, `author`, `date`, and `abstract`.
  3. Streamlined `styles/i18n/forensic/en.json` to `"examiner_label": "EXAMINER:"` and updated `styles/forensic.css` with `min-width: 7.5rem; margin-right: 0.5rem; flex-shrink: 0;` to prevent text wrapping issues.

---

## 5. Visual Regression Fix & Pure Triple CSS Cascade Restoration

### 1. Root Cause of Visual Degradation
- During experimental manifest decoupling, the explicit triple CSS cascade was bypassed:
  - `styles/fonts.css` (JetBrains Mono and Inter embedded WOFF2 fonts)
  - `styles/base.css` (container resets, card styles, base typography, alerts)
  - `styles/{theme}.css` (theme-specific variables, dark palettes, interactive components)
- In addition, premature injection of `@media print` rules and paged layouts corrupted screen-mode styling (such as dark themes turning light gray).
- Furthermore, prepending raw `<style>` tags to the Markdown stream broke Pandoc's frontmatter parser, preventing the extraction of `title`, `author`, `date`, and `abstract`.

### 2. Concrete Resolution
1. **Restored Proven Triple Cascade**:
   - In [`core/engine.py`](file:///home/valor/Devel/personal/md-style/core/engine.py), Pandoc always loads `fonts.css`, followed by `base.css`, followed by the resolved theme stylesheet (`css_path`).
   - Print stylesheets (`styles/print.css`) and `paged.css` are strictly isolated to `--print` and `--paged` CLI modes.
2. **Headless Chromium Header/Footer Suppression**:
   - Switched to the official `--no-pdf-header-footer` Chromium flag in `core/engine.py`.
   - Verified with `pdftotext` that browser timestamps, page numbers, and `file:///` URLs are completely suppressed in PDF outputs.
3. **Clean Frontmatter & Header Injection**:
   - CSS custom properties (`:root { ... }`) for i18n are injected via `--include-in-header` using a temporary HTML snippet, leaving line 1 of the Markdown source (`---`) pristine for Pandoc.
   - Restored `#title-block-header` styling with `.abstract`, `p.author` (`EXAMINER:`), and `p.date`.
4. **Forensic Word-Wrapping & CVE Enrichment**:
   - Hardened `styles/forensic.css` and `styles/forensic-cyber.css` with `white-space: nowrap !important; word-break: keep-all !important;` for IoCs, pills, and timestamps, while hashes cleanly wrap (`word-break: break-all !important;`).
5. **Table Filter Headers & Category Discovery**:
   - In [`templates/forensic-cyber-interactive.html`](file:///home/valor/Devel/personal/md-style/templates/forensic-cyber-interactive.html), fixed `ReferenceError: uiStrings is not defined` by initializing `uiStrings` at closure scope.
   - Synchronized DOM construction to match `.table-filter-toolbar`, `.table-filter-main`, `.table-filter-search-wrap`, `.table-filter-counter`, and `.filter-pill` in [`styles/forensic-cyber.css`](file:///home/valor/Devel/personal/md-style/styles/forensic-cyber.css).
6. **Eliminated Doubled Callout Icons**:
   - **Root Cause**: An experimental attempt to replace `filters/callouts.lua` had added CSS mask icons (`div.* .title::before`) into [`styles/base.css`](file:///home/valor/Devel/personal/md-style/styles/base.css). When `callouts.lua` was restored, both the CSS pseudo-element `::before` and the filter's inline SVG `<span class="callout-icon">` rendered simultaneously, causing doubled icons.
   - **Resolution**: Removed redundant `div.* .title::before` rules from `styles/base.css` and restored pure `.callout-icon` and `.octicon` typography rules. Corrected the octicon mapping for `[!IMPORTANT]` in [`filters/callouts.lua`](file:///home/valor/Devel/personal/md-style/filters/callouts.lua) from `"important"` to `"report"`. Verified in headless Chrome that all callouts (`NOTE`, `TIP`, `IMPORTANT`, `WARNING`, `CAUTION`) display exactly one icon.

### 3. Verification Across Styles & Formats
- `forensic-cyber` (HTML & PDF): Dark theme container, fonts, Mermaid charts, interactive HUD, IoC drawer, and CVSS cards 100% verified. Interactive table filter toolbars verified across all 4 tables with live search and pill filters.
- `forensic` (HTML & PDF): Title block header, examiner badge, date, executive abstract, and timeline table verified with zero browser header/footer leaks.
- `school` & `svj/invitation` (HTML & PDF): Fast compilation, typography, and clean layouts verified.
- `tests/test-custom-kb.md`, `tests/test-eid.md`, `tests/test-gfm-features.md`: All passed cleanly. Verified single icons on all GFM alert callouts.

