# Walkthrough: Paged.js Removal, Single-Source PDF Printing & Forensic i18n Fixes

## 1. Executive Summary & Root Cause Analysis

Following user feedback on duplicated headers/footers in `--pdf`, English strings appearing in Czech forensic reports, and doubled frontmatter badges/author labels, we performed a full architectural cleanup:

### Root Causes & Fixes
1. **Duplicate Headers & Footers in `--pdf`**:
   - Modern Chromium (131+) supports CSS Paged Media `@page` margin boxes (`@top-left`, `@bottom-right`).
   - Simultaneously, our CDP print script was passing `displayHeaderFooter: true` with rich HTML templates.
   - Chromium printed **both** systems simultaneously.
   - **Fix**: Removed margin boxes (`@top-*`, `@bottom-*`) from `styles/base/paged.css`. Left `@page { size: A4 portrait; margin: ... }` for page geometry, making CDP `headerTemplate` and `footerTemplate` the **sole authoritative printer**.
2. **Permanent Removal of Paged.js**:
   - Paged.js was completely uninstalled from `viewer/package.json` and `viewer/src/App.svelte`.
   - Replaced with a non-destructive pure-CSS **"Paper View"** (`.sheet-view`) that formats content into centered A4 proportions (`max-width: 210mm; min-height: 297mm; padding: 25mm 20mm;`) with drop shadows, without touching or cloning any DOM elements.
   - The HUD toggle allows instant switching between **"🖥️ Web View"** and **"📄 Paper View"**, while a dedicated **"🖨️ Print / PDF"** button triggers native `window.print()`.
3. **Forensic Report i18n Localization in Czech**:
   - Synchronized forensic keys (`examiner`, `lead_examiner`, `date`, `case_id`, `report_title`, `classification`, `unit`) across `core/i18n/cs.json`, `en.json`, `sk.json`, and `de.json`.
   - Added `--i18n-confidential` alias in `core/i18n/__init__.py`.
   - Updated `core/engine.py` `_build_dossier_header()` to cascade through `forensics.examiner`, `meta.examiner_label`, and `meta.author_label`.
4. **Eliminated Doubled Frontmatter Text**:
   - Removed legacy `#title-block-header::before`, `p.author::before`, and `p.date::before` from `styles/forensic/dossier/forensic.css`.
   - Added anti-duplication CSS rules to `styles/base/base.css` (`#title-block-header:has(.report-badge)::before { display: none !important; }`).
   - Added regex prefix stripping in `core/engine.py` to sanitize leading role prefixes from the author string (e.g., removing `Lead Examiner:` when the template already adds `<span class="meta-label">Examiner:</span>`).
5. **Scoped Table of Contents**:
   - Enhanced `core/parser/plugins/toc.py` to support `{{#toc section="..."}}`, `{{toc section="..."}}`, and `[[TOC section="..."]]` in addition to `::: {#toc section="..."}`.
   - In `examples/pozvánka-shromáždění-svj.md`, configured `::: {#toc section="Detaily jednání"}` so that the agenda TOC only extracts subheadings from the "Detaily jednání" section.

---

## 2. Verification Results

### A. PDF Single Header / Footer Verification
Generated `examples/sample-forensic-report.md` via `--pdf`:
```text
Page 1:
TOP: ['Digital Forensic Investigation Report', 'CONFIDENTIAL // TLP:AMBER', 'FORENSIC INVESTIGATION REPORT']
BOTTOM: ['Forensic Investigation Unit', 'September 11, 2026 • SHA-256:', 'Page 1 of 10']

Page 2:
TOP: ['Digital Forensic Investigation Report', 'CONFIDENTIAL // TLP:AMBER', 'CRITICAL FINDING']
BOTTOM: ['Forensic Investigation Unit', 'September 11, 2026 • SHA-256:', 'Page 2 of 10']
```
- Exactly **ONE** header per page (`Digital Forensic Investigation Report` | `CONFIDENTIAL // TLP:AMBER`).
- Exactly **ONE** footer per page (`Forensic Investigation Unit` | `Date • Hash` | `Page X of Y`).
- Single badge (`FORENSIC INVESTIGATION REPORT`), no duplicate badge.
- Single examiner label (`Examiner: S. Mercer...`), no duplicate `Lead Examiner:` prefix.

### B. Czech Forensic Document Verification
Generated Czech forensic report (`test_cs_forensic.md`):
```text
TOP: ['Zpráva z digitálního forenzního vyšetřování', 'PŘÍSNĚ TAJNÉ // TLP:AMBER', ...]
BOTTOM: ['Forenzní vyšetřovací jednotka', '9. října 2026 • SHA-256:', 'Strana 1 z 1']
```
- Footer is localized: `Forenzní vyšetřovací jednotka` | `Strana 1 z 1`.
- Metadata is localized: `Vyšetřovatel: Ing. Jan Novák...`, `Datum: 9. října 2026`, `SHRNUTÍ ZJIŠTĚNÍ`.

### C. SVJ Scoped Agenda TOC Verification
Generated `examples/pozvánka-shromáždění-svj.md`:
```html
<div class="agenda-toc-container">
  <div class="toc-title">Program shromáždění</div>
  <ol class="agenda-toc-list">
    <li><a href="#zahájení">Zahájení</a></li>
    <li><a href="#zpráva-výboru-o-hospodaření-a-schválení-účetní-závěrky-za-rok-2025">Zpráva výboru o hospodaření...</a></li>
    <li><a href="#zpráva-o-technickém-stavu-budovy-a-provedených-opravách">Zpráva o technickém stavu...</a></li>
    <li><a href="#rozúčtování-nákladů-instalace-dálkových-odečtů-měřidel">Rozúčtování nákladů...</a></li>
```
- Only items from `Detaily jednání` (Zahájení, Zpráva výboru, Technický stav, etc.) are present.
- Administrative headings (`Termín a místo konání`, `Program shromáždění`) are excluded.

### D. Automated Pytest Suite
```bash
uv run pytest
```
Output:
```text
============================== 63 passed in 3.15s ==============================
```
