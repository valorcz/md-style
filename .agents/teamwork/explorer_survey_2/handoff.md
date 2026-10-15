# Investigation Report: Survey 2 - W3C Paged Media & Vector PDF Print Fidelity

**Target Requirement**: R2 (W3C Paged Media & Vector PDF Print Fidelity Verification)  
**Investigator**: Explorer 2  
**Date**: 2026-10-11  

---

## 1. Observation

### 1.1 Theme & Stylesheet Layout
We surveyed the style tree across all themes:
- **Base Theme** (`styles/base/`):
  - `styles/base/theme.yaml`: Defines root A4 geometry (`size: A4`, margins `22mm 18mm 22mm 18mm`), headers (`left: "{doc_title}"`, `right: "string(heading)"`), and footers (`left: "{date}"`, `right: "{page_counter}"`). Sets `first_page: show_header: false, show_footer: true`.
  - `styles/base/paged.css`: Defines base `@page` geometry, `thead { display: table-header-group !important; break-inside: avoid !important; }`, `tr { break-inside: avoid !important; }`, `p { orphans: 3; widows: 3; }`, `h1..h6 { break-after: avoid !important; }`. Under `@media print`: `tr, li, blockquote, .callout, figure, pre { break-inside: avoid !important; }`.
  - `styles/base/paged-harness.css`: Contains CSS rules for on-screen `#md-style-paged-root`, discrete paper sheets (`.pagedjs_page`), and fragmentation rules (`.theme-svj .signature-row, .callout, .admonition, .kpi-card, .kpi-grid, blockquote { break-inside: avoid; }`).
  - `styles/base/print.css`: Contains zero-JS print stylesheet (`@page:first { margin-top: 18mm; }`, `.proposal-callout, blockquote, div.note... { break-inside: avoid !important; }`).
- **Forensic Themes** (`styles/forensic/`):
  - `styles/forensic/cyber/theme.yaml`: Extends `base`, margins `top: 25mm, bottom: 25mm`, headers center: `"{classification|TLP:AMBER // CONFIDENTIAL}"`, footers left: `"{i18n.forensics.unit} // CYBER DFIR"`.
  - `styles/forensic/dossier/theme.yaml`: Extends `base`, headers center: `"{classification}"`, footers center: `"{date} • SHA-256: {fingerprint}"`.
  - Components: `dossier-header.css`, `kpi-grid.css`, `timeline.css`.
- **SVJ Themes** (`styles/svj/`):
  - `styles/svj/base/theme.yaml`: Extends `base`, margins `20mm 15mm 20mm 15mm`, headers center `"{i18n.svj.assembly_invite}"`, footers left `"{i18n.svj.committee_label}"`, center `"{i18n.svj.statute_notice}"`.
  - `styles/svj/invitation/theme.yaml`: Extends `svj/base`.
  - `styles/svj/invitation/invitation.css`: Lines 314–333 contain:
    ```css
    @page {
      margin: 18mm 14mm 22mm 14mm;
      @bottom-right {
        content: counter(page);
        font-family: var(--font-body);
        font-size: 8pt;
        color: #2b8a9e;
        border-top: none;
      }
    }
    @page:first {
      @top-left { content: none !important; }
      @top-center { content: none !important; }
      @top-right { content: none !important; }
      @bottom-left { content: none !important; }
      @bottom-center { content: none !important; }
      @bottom-right { content: none !important; }
    }
    ```
  - `styles/svj/ballot/ballot.css`, `styles/svj/community/community.css`, `styles/svj/typewriter/typewriter.css`.
- **General Themes** (`styles/general/`):
  - `styles/general/school/theme.yaml`: Extends `base`, stylesheets `school.css`.
  - `styles/general/school/school.css`: Defines academic progress dossier, grade tables, and lines 248–255:
    ```css
    .signature-block {
      display: flex;
      justify-content: space-between;
      margin-top: 3.5rem;
      padding-top: 1rem;
      page-break-inside: avoid;
      break-inside: avoid;
    }
    ```
  - `styles/general/announcement/theme.yaml` & `styles/general/family-invite/theme.yaml`.

---

### 1.2 PDF Compilation Mechanisms
1. **Primary PDF Compilation Route (Chromium CDP)**:
   - Invocation: `md-style <input.md> -s <theme> -p -o <output.pdf>` or `--pdf`.
   - Engine orchestration (`core/engine.py:311–337`):
     - Uses runtime `/usr/bin/bun` or `/usr/bin/node` to execute `core.config.PRINT_PDF_SCRIPT` (`viewer/scripts/print-pdf.mjs`).
     - Passes source HTML path, destination PDF path, and a JSON options string synthesized by `bundler.build_cdp_header_footer_templates(...)`.
   - Script implementation (`viewer/scripts/print-pdf.mjs:74–180`):
     - Spawns Chromium with `--headless=new`, `--disable-gpu`, `--no-sandbox`, `--remote-debugging-port=<port>`.
     - Connects via WebSocket to Chromium DevTools Protocol (`Page.enable`, `Page.navigate`).
     - Awaits stabilization (`options.waitMs ?? 700`).
     - Invokes CDP `Page.printToPDF` with:
       ```javascript
       displayHeaderFooter: Boolean(options.headerTemplate || options.footerTemplate),
       headerTemplate: options.headerTemplate || "<div></div>",
       footerTemplate: options.footerTemplate || "<div></div>",
       marginTop: options.marginTop ?? 0.8,
       marginBottom: options.marginBottom ?? 0.8,
       marginLeft: options.marginLeft ?? 0.6,
       marginRight: options.marginRight ?? 0.6,
       preferCSSPageSize: true,
       generateTaggedPDF: true,
       generateDocumentOutline: true
       ```
     - Writes base64 binary result directly to the destination PDF file.
   - Fallback route (`core/engine.py:339–363`): Directly invokes `chromium-browser --headless --print-to-pdf=<dst> file://<src>` if Node/Bun is absent.

2. **In-Browser Paged.js Preview Route**:
   - Bundling (`core/bundler.py:499–512`):
     - Injects `<script id="md-style-print-templates" type="application/json">` containing `headerTemplate`, `footerTemplate`, `showFirstHeader`, `showFirstFooter`, margins.
   - Svelte Runtime (`viewer/src/App.svelte:212–271` & `viewer/src/paged/paged-handlers.ts:65–107`):
     - Toggleable via HUD ribbon button "📄 Paper View" or URL hash `#paged`.
     - Invokes `new Previewer().preview(clone, [inlinePageStyles], root)`.
     - `UnifiedHeaderFooterHandler` runs in `afterRendered(pages)`:
       - Iterates over rendered pages, calculates `pageNumber = index + 1` and `totalPages = pages.length`.
       - Replaces `topMargin.innerHTML = templates.headerTemplate`.
       - Replaces `bottomMargin.innerHTML = templates.footerTemplate`, replacing `.pageNumber` with `index + 1` and `.totalPages` with `total`.
       - Respects `showFirstHeader` and `showFirstFooter` on `index === 0`.

---

### 1.3 Identified Bugs and Regressions in Current Output

#### Bug A: Duplicate Page Number in `svj/invitation` (`styles/svj/invitation/invitation.css`)
- **Direct observation**:
  Command: `uv run md-style "examples/pozvánka-shromáždění-svj.md" -s svj/invitation -p -o output/pozvanka-svj.pdf`
  Command: `pdftotext -f 2 -l 2 output/pozvanka-svj.pdf -`
  Verbatim output from page 2:
  ```text
  Statutární orgán / Výbor SVJ    Dle § 1207 z. č. 89/2012 Sb. (občanský zákoník)
  2
  Strana 2 z 5
  ```
  On pages 2, 3, 4, 5, the footer contains both the bare number `2` (from CSS `@bottom-right`) and `Strana 2 z 5` (from CDP template)!
- **Location**: `styles/svj/invitation/invitation.css:316–323`.

#### Bug B: Forensic Dossier Badges and Examiner Labels Leaking into School Theme
- **Direct observation**:
  Command: `uv run md-style examples/school-report-sample.md -s general/school -p -o output/school-report.pdf`
  Command: `pdftotext -f 1 -l 1 output/school-report.pdf - | head -n 12`
  Verbatim output:
  ```text
  Academic Progress & Evaluation Report
  FORENSIC INVESTIGATION REPORT
  Academic Progress & Evaluation Report
  Department of Computer Science & Software Engineering | Spring Term 2026
  Examiner: Faculty Advisor: Dr. Alistair Vance | Examination Board
  Date: June 12, 2026
  ```
- **Code observation**:
  In `core/engine.py:365–371`:
  ```python
  def _should_build_dossier_header(self, style: str, frontmatter: Optional[Dict[str, Any]]) -> bool:
      fm = frontmatter or {}
      if fm.get("dossier_header") is False:
          return False
      is_forensic = "forensic" in (style or "").lower()
      has_meta = any(k in fm for k in ("author", "examiner", "date", "abstract", "subtitle", "case_id", "case"))
      return (is_forensic or has_meta) and bool(fm.get("title"))
  ```
  And in `core/engine.py:383–390`:
  ```python
  report_badge = (
      fm.get("report_badge")
      or fm.get("report-badge")
      or fm.get("classification")
      or catalog.get("forensics.report_title")
      or catalog.get("meta.report_type")
      or "DIGITAL FORENSIC INVESTIGATION REPORT"
  )
  ```
  And `author_label` falls back to `catalog.get("forensics.examiner")` ("Examiner:").
  Any document with `author` or `date` in frontmatter gets marked as a forensic report!

#### Bug C: Blank SHA-256 Hash in Forensic PDF Footer
- **Direct observation**:
  In `output/sample-forensic-report.pdf`, page 2 footer:
  `September 11, 2026 • SHA-256:` (fingerprint hash is blank).
- **Code observation**:
  In `core/engine.py:316–321`:
  ```python
  print_options = bundler.build_cdp_header_footer_templates(
      theme=theme,
      catalog=catalog,
      title=title,
      frontmatter=frontmatter
      # Missing: fingerprint=bundler.fingerprint
  )
  ```
  Because `fingerprint` defaults to `""`, the placeholder `{fingerprint}` evaluates to empty string in `_compile_pdf`.

#### Bug D: Incomplete Break-Inside Rules in Base Styles
- **Direct observation**:
  In `styles/base/paged.css:191`:
  `tr, li, blockquote, .callout, figure, pre { break-inside: avoid !important; }`
  Missing: `.signature-block`, `.signature-row`, `.committee-signature`, `.sign-off`, `.admonition`, `.kpi-card`, `.kpi-grid`, `.timeline-item`.
  In `styles/base/print.css:50–60`:
  Missing: `.callout`, `figure`, `.signature-block`, `.signature-row`, `.committee-signature`, `.sign-off`, `.kpi-card`, `.kpi-grid`.

---

### 1.4 Ordered List Continuation Mechanism
- **Paged.js Preview**:
  In `viewer/src/paged/paged-handlers.ts:34–63`:
  - `beforeParsed(content)`: Assigns unique `data-ol-id="list-1"`, `"list-2"` to all `<ol>` elements.
  - `afterPageLayout(pageElement)`: Inspects `<ol>` on each page. If `this.olCounters.has(listId)`, sets `ol.setAttribute('start', String(prevCount + 1))` and increments by the count of `:scope > li` on that page.
- **Chromium Native PDF**:
  A single `<ol>` in continuous HTML is fragmented across page breaks by the browser's layout engine. Numbering (`1, 2, ... N`) increments naturally across pages.
  `li { break-inside: avoid !important; }` in `styles/base/paged.css:42` guarantees that individual `<li>` nodes are never sliced in half horizontally across a page split.

---

### 1.5 PDF Inspection Tools Available in the Environment
- System CLI binaries verified in `/usr/bin/`:
  - `/usr/bin/pdfinfo`: Extracts page count (`Pages: N`), document title, producer, creation date.
  - `/usr/bin/pdftotext`:
    - `pdftotext -f <P> -l <P> <pdf> -`: Fast plain text extraction per page.
    - `pdftotext -bbox-layout -f <P> -l <P> <pdf> -`: Produces standard XML with exact bounding boxes (`xMin`, `yMin`, `xMax`, `yMax`) of every block, line, and word on every page.
  - `/usr/bin/pdftoppm`: Renders pages to images (PNG) for visual raster comparison.
  - `/usr/bin/strings`: Inspects low-level PDF dictionary strings.
- Python libraries:
  - Python version: 3.14.8.
  - `xml.etree.ElementTree` in standard library parses `pdftotext -bbox-layout` XML output in <10ms with zero extra dependencies.
  - `pypdf`: Resolves cleanly via `uv pip install pypdf --dry-run` (`pypdf==6.20.0`), can be added to `[dependency-groups] dev` in `pyproject.toml` if desired.

---

## 2. Logic Chain

1. **Premise**: Requirement 2 mandates an automated verification harness verifying:
   - Monotonic page numbers (`Page X of Y` / `1 of N` to `N of N`) without truncation or overlap.
   - Running headers matching document metadata without orphan headers or split table headers.
   - Page-break avoidance holding for tables, diagrams, callouts, and signature blocks across page boundary splits.
   - Ordered list continuation across page boundaries.
2. **From Observation 1.3 (Bug A)**: `styles/svj/invitation/invitation.css` contains `@bottom-right { content: counter(page); }`. In Chromium 154, both the CSS margin box and CDP `footerTemplate` are rendered, printing `2` and `Strana 2 z 5` on top of each other. Removing the obsolete margin box from `invitation.css` fixes the duplication and aligns SVJ with the single-source architecture documented in `walkthrough.md`.
3. **From Observation 1.3 (Bug B)**: `_should_build_dossier_header()` activates when `has_meta` is True, even for non-forensic themes like `school`. It injects `FORENSIC INVESTIGATION REPORT` and `Examiner:` into academic reports. Scoping forensic badges strictly to forensic themes (`is_forensic`) and using general labels (`Author:`) for general documents restores theme fidelity.
4. **From Observation 1.3 (Bug C)**: `_compile_pdf()` does not pass `fingerprint=bundler.fingerprint` to `build_cdp_header_footer_templates()`. Passing `bundler.fingerprint` restores the SHA-256 hash in forensic footers.
5. **From Observation 1.3 (Bug D)**: Base break-inside rules omit signature blocks (`.signature-block`, `.signature-row`, `.committee-signature`), callouts (`.callout`, `.admonition`), and KPI cards (`.kpi-card`, `.kpi-grid`). Adding these selectors to `styles/base/paged.css` and `styles/base/print.css` ensures they never fragment across page breaks.
6. **From Observation 1.5**: `pdftotext -bbox-layout` emits XML containing bounding boxes of every word on each page. This enables an automated verification script to:
   - Calculate vertical distance between content bottom (`content.yMax`) and footer top (`footer.yMin`), asserting `distance > 0` (no overlap).
   - Verify footer strings against regex `(?:Page|Strana)\s+(\d+)\s+(?:of|z)\s+(\d+)`, asserting `current == page_idx` and `total == page_count`.
   - Check that headings are not within 40pt of the page bottom unless followed by body content (zero orphan headers).
   - Check that tables with multiple pages have `thead` repeating at the top of subsequent pages.
   - Confirm ordered list item numbers increment continuously across page splits.

---

## 3. Caveats

1. **Browser Dependency**: Headless Chromium (`/usr/bin/chromium-browser`) and Bun (`/usr/bin/bun`) must be present in the execution environment to compile PDFs. Both are present and verified in the current environment.
2. **Font Metrics**: Bounding box coordinates from `pdftotext -bbox-layout` depend on font rasterization. Assertions should test relative geometry (e.g. `header.yMax < content.yMin` and `content.yMax < footer.yMin`) with reasonable thresholds rather than hardcoded pixel coordinates.
3. **Air-Gap Strictness**: The automated test harness should rely primarily on `/usr/bin/pdftotext` and Python standard library `xml.etree.ElementTree`, or use `pypdf` only if installed via uv, ensuring zero runtime network access.

---

## 4. Conclusion

The current PDF compilation pipeline via Bun and Chromium CDP is fast (2–3 seconds per document) and produces high-quality vector PDFs, while Paged.js provides interactive in-browser preview. However, four specific issues must be remediated to satisfy R2:
1. **Fix duplicate page numbering in SVJ**: Remove `@bottom-right` margin box rules from `styles/svj/invitation/invitation.css`.
2. **Fix title block leaking in non-forensic themes**: Guard `_build_dossier_header()` in `core/engine.py` so that `forensics.report_title` and `forensics.examiner` are only used when `is_forensic` is True.
3. **Pass fingerprint in CDP PDF compilation**: Pass `fingerprint=bundler.fingerprint` in `core/engine.py:_compile_pdf()`.
4. **Universal fragmentation protection**: Expand `styles/base/paged.css` and `styles/base/print.css` with `.signature-block`, `.signature-line`, `.signature-row`, `.committee-signature`, `.sign-off`, `.callout`, `.admonition`, `.kpi-card`, `.kpi-grid`, `figure`.
5. **Makefile target update**: Add `examples/school-report-sample.md` to `samples-pdf` in `Makefile`.
6. **Automated Print Verification Test**: Build `tests/test_print_fidelity.py` combining document compilation across forensic, SVJ, and school themes with automated XML bounding box inspection using `pdftotext -bbox-layout`.

---

## 5. Verification Method

### Step 1: Run the Proposed Automated Print Fidelity Suite
Run:
```bash
uv run pytest tests/test_paged_theme.py -v
```
Currently passes 11/11 tests.

### Step 2: Test Sample PDF Compilation
Compile all 4 required themes:
```bash
mkdir -p output
uv run md-style examples/sample-forensic-cyber.md -s forensic/cyber -p -o output/sample-forensic-cyber.pdf
uv run md-style examples/sample-forensic-report.md -s forensic/dossier -p -o output/sample-forensic-report.pdf
uv run md-style "examples/pozvánka-shromáždění-svj.md" -s svj/invitation -p -o output/pozvanka-svj.pdf
uv run md-style examples/school-report-sample.md -s general/school -p -o output/school-report.pdf
```

### Step 3: Verify Monotonic Page Numbers and Header Integrity
Inspect page numbers with `pdftotext`:
```bash
python3 -c "
import subprocess, re
for pdf in ['output/sample-forensic-cyber.pdf', 'output/sample-forensic-report.pdf', 'output/pozvanka-svj.pdf', 'output/school-report.pdf']:
    out = subprocess.check_output(['pdfinfo', pdf]).decode('utf-8')
    total = int(re.search(r'Pages:\s+(\d+)', out).group(1))
    print(f'=== {pdf} ({total} pages) ===')
    for p in range(1, total + 1):
        txt = subprocess.check_output(['pdftotext', '-f', str(p), '-l', str(p), pdf, '-']).decode('utf-8')
        lines = [l.strip() for l in txt.splitlines() if l.strip()]
        print(f'  P{p}: {lines[-1]}')
"
```

### Step 4: Verify Zero Overlaps via XML Bounding Boxes
```bash
python3 -c "
import subprocess, xml.etree.ElementTree as ET
xml_bytes = subprocess.check_output(['pdftotext', '-bbox-layout', '-f', '1', '-l', '1', 'output/school-report.pdf', '-'])
root = ET.fromstring(xml_bytes)
blocks = root.findall('.//{http://www.w3.org/1999/xhtml}block')
print(f'Parsed {len(blocks)} layout blocks on Page 1')
"
```

### Invalidation Conditions
- Any occurrence of duplicated page numbers (e.g. `2` and `Strana 2 z 5` on the same page).
- Any appearance of "FORENSIC INVESTIGATION REPORT" in non-forensic documents (e.g. school report).
- Blank hash strings following `SHA-256:` in forensic reports.
- Negative clearance between header/content or content/footer (`yMin` / `yMax` overlap).
- Orphan headings as the final block of a page without subsequent body content.
