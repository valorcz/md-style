# Handoff Report: Explorer M2.1 - Print Stylesheets & Break Avoidance

**Target Scope**: Milestone M2 (Print Fidelity & Theme Fixes)  
**Investigator**: Explorer M2.1  
**Date**: 2026-10-11  
**Status**: Investigation Complete  

---

## 1. Observation

### 1.1 Duplicate Page Counter in `styles/svj/invitation/invitation.css`
- **File location**: `styles/svj/invitation/invitation.css:314–333`
- **Verbatim source snippet**:
  ```css
  /* --------------------------------------------------------------------------
     Paged Media Adjustments
     -------------------------------------------------------------------------- */
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

  /* Suppress all headers and footers on Page 1 */
  @page:first {
    @top-left { content: none !important; }
    @top-center { content: none !important; }
    @top-right { content: none !important; }
    @bottom-left { content: none !important; }
    @bottom-center { content: none !important; }
    @bottom-right { content: none !important; }
  }
  ```
- **Observed PDF output**:
  When compiling `examples/pozvánka-shromáždění-svj.md` via `uv run md-style "examples/pozvánka-shromáždění-svj.md" -s svj/invitation -p -o output/test_pozvanka.pdf`, running `pdftotext -f 2 -l 2 output/test_pozvanka.pdf -` outputs on page 2:
  ```text
  Statutární orgán / Výbor SVJ

  Dle § 1207 z. č. 89/2012 Sb. (občanský zákoník)

  2

  Strana 2 z 5
  ```
  Both the CSS `@bottom-right` counter `2` and the CDP footer template `Strana 2 z 5` are rendered simultaneously on pages 2, 3, 4, 5.
- **Architectural context**: In `docs/plans/walkthrough.md:12`, modern Chromium 131+ supports CSS Paged Media `@page` margin boxes as well as CDP `displayHeaderFooter`. The project established CDP templates as the **sole authoritative printer** for headers and footers, removing all `@top-*` and `@bottom-*` rules from base styles (`styles/base/paged.css`). `styles/svj/invitation/invitation.css` is the only remaining stylesheet in the repository that still defines `@bottom-right`.
- **Sister SVJ themes**: In `styles/svj/base/svj-base.css:348–350`, `styles/svj/community/community.css:372–374`, and `styles/svj/typewriter/typewriter.css:349–351`, the `@page:first` rule contains exclusively:
  ```css
  @page:first {
    margin-top: 18mm;
  }
  ```
  with zero margin box rules.

---

### 1.2 Incomplete Break-Inside Rules in `styles/base/paged.css`
- **File location**: `styles/base/paged.css`
- **Section 3 (`styles/base/paged.css:35–50`)**:
  ```css
  /* Orphan, widow, heading and list item break protection across all themes */
  p {
    orphans: 3;
    widows: 3;
  }

  li {
    break-inside: avoid !important;
    page-break-inside: avoid !important;
  }

  h1, h2, h3, h4, h5, h6,
  .agenda-heading {
    break-after: avoid !important;
    page-break-after: avoid !important;
  }
  ```
  *Observation*: Section 3 applies to all media types. Only `li`, `thead`, and `tr` have break-inside protection. Critical document components (`.signature-block`, `.signature-line`, `.signature-row`, `.committee-signature`, `.sign-off`, `.callout`, `.admonition`, `.kpi-card`, `.kpi-grid`, `figure`) are absent.
- **Section 8 (`styles/base/paged.css:190–192`)**:
  ```css
    tr, li, blockquote, .callout, figure, pre {
      break-inside: avoid !important;
    }
  ```
  *Observation*: Only `.callout` and `figure` are present. Missing: `.signature-block`, `.signature-line`, `.signature-row`, `.committee-signature`, `.sign-off`, `.admonition`, `.kpi-card`, `.kpi-grid`. Also lacks the legacy fallback `page-break-inside: avoid !important`.

---

### 1.3 Incomplete Break-Inside Rules in `styles/base/print.css`
- **File location**: `styles/base/print.css:50–60`
- **Verbatim source snippet**:
  ```css
  .proposal-callout,
  blockquote,
  div.note,
  div.warning,
  div.tip,
  div.important,
  div.caution,
  div.critical {
    break-inside: avoid !important;
    page-break-inside: avoid !important;
  }
  ```
  *Observation*: `print.css` provides the zero-JS native print stylesheet. It currently only protects `.proposal-callout`, `blockquote`, and alert div types (`div.note`, etc.). It completely lacks `.callout`, `.admonition`, `figure`, `.signature-block`, `.signature-line`, `.signature-row`, `.committee-signature`, `.sign-off`, `.kpi-card`, `.kpi-grid`.

---

### 1.4 Target Selector Inventory Across the Codebase
- `.signature-block` and `.signature-line`: Used in `styles/general/school/school.css:248–265` and `examples/school-report-sample.md:68–78` (`::: {.signature-block}`).
- `.signature-row`: Used in `styles/base/paged-harness.css:125`.
- `.committee-signature` and `.sign-off`: Used in `styles/svj/base/svj-base.css:353–359`, `styles/svj/community/community.css:360–365`, `styles/svj/typewriter/typewriter.css:324–330`.
- `.callout`: Used universally in `styles/base/base.css:386`, `styles/forensic/cyber/cyber.css:685`, and Markdown alerts (`div.callout`).
- `.admonition`: Standard Sphinx/Pandoc/MkDocs admonition container class (`styles/base/paged-harness.css:127`).
- `.kpi-card` and `.kpi-grid`: Used in `styles/forensic/components/kpi-grid.css:4–11`, `styles/forensic/cyber/cyber.css:600–615`, `styles/forensic/dossier/forensic.css:1128–1135`.
- `figure`: Standard HTML5 `<figure>` wrapping diagrams, charts, and captioned code blocks.

---

## 2. Logic Chain

1. **Root cause of duplicate SVJ page numbers**:
   - `styles/base/theme.yaml` defines `footers.right: "{page_counter}"`.
   - `styles/svj/base/theme.yaml` inherits from `base`, leaving `footers.right` active.
   - `core/bundler.py` synthesizes CDP footer templates containing `Strana <span class="pageNumber"></span> z <span class="totalPages"></span>`.
   - `styles/svj/invitation/invitation.css` concurrently defines `@page { @bottom-right { content: counter(page); } }`.
   - In Chromium 131+, both mechanisms execute simultaneously, generating the duplicate counter `2` superimposed over `Strana 2 z 5` on every page starting at page 2.
   - Therefore, removing `@bottom-right` from `invitation.css` eliminates the duplicate and establishes CDP templates as the single authoritative source of truth, matching all other themes.
   - Aligning `@page:first` with `margin-top: 18mm;` matches the convention established in `svj-base.css`, `community.css`, and `typewriter.css`.

2. **Universal fragmentation protection**:
   - Documents with signature sections (e.g., academic grade dossiers, legal notices, committee ballots) must never have signatures sliced across page boundaries.
   - Complex callouts, admonitions, KPI dashboard cards, and diagram figures that are fragmented across page splits degrade document legibility and break layout consistency.
   - While some individual themes included local rules (e.g. `school.css` for `.signature-block` or `kpi-grid.css` for `.kpi-card`), the base stylesheets (`styles/base/paged.css` and `styles/base/print.css`) are loaded globally for all themes in print/PDF mode.
   - Adding all 10 selectors (`.signature-block`, `.signature-line`, `.signature-row`, `.committee-signature`, `.sign-off`, `.callout`, `.admonition`, `.kpi-card`, `.kpi-grid`, `figure`) with both `break-inside: avoid !important;` and `page-break-inside: avoid !important;` to `styles/base/paged.css` (both Section 3 universal and Section 8 `@media print`) and `styles/base/print.css` (Section 3) guarantees deterministic, unbreakable rendering across all themes in both Chromium CDP vector printing and native browser printing.

---

## 3. Caveats

1. **Container Height Overflow**: If a single element (such as a very large figure or huge table) is taller than an entire A4 page (height > 297mm minus margins), `break-inside: avoid` will force it to the next page, but cannot prevent it from overflowing the page bottom if it still exceeds page height. This is expected CSS Paged Media behavior.
2. **Read-Only Investigation**: In accordance with the Teamwork explorer persona, these patches are formulated and verified without modifying the repository source files. The implementer agent will apply the patches.

---

## 4. Conclusion & Exact Proposed Patches

### 4.1 Patch 1: `styles/svj/invitation/invitation.css`

#### Target File
`/home/valor/Devel/personal/md-style/styles/svj/invitation/invitation.css` (Lines 314–333)

#### Proposed Unified Diff
```diff
--- a/styles/svj/invitation/invitation.css
+++ b/styles/svj/invitation/invitation.css
@@ -314,23 +314,11 @@
 @page {
   margin: 18mm 14mm 22mm 14mm;
-  @bottom-right {
-    content: counter(page);
-    font-family: var(--font-body);
-    font-size: 8pt;
-    color: #2b8a9e;
-    border-top: none;
-  }
 }
 
-/* Suppress all headers and footers on Page 1 */
+/* Page 1 Margin Adjustment */
 @page:first {
-  @top-left { content: none !important; }
-  @top-center { content: none !important; }
-  @top-right { content: none !important; }
-  @bottom-left { content: none !important; }
-  @bottom-center { content: none !important; }
-  @bottom-right { content: none !important; }
+  margin-top: 18mm;
 }
 
 @media print {
```

#### Code Snippet (Before vs After)
**Before**:
```css
/* --------------------------------------------------------------------------
   Paged Media Adjustments
   -------------------------------------------------------------------------- */
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

/* Suppress all headers and footers on Page 1 */
@page:first {
  @top-left { content: none !important; }
  @top-center { content: none !important; }
  @top-right { content: none !important; }
  @bottom-left { content: none !important; }
  @bottom-center { content: none !important; }
  @bottom-right { content: none !important; }
}
```

**After**:
```css
/* --------------------------------------------------------------------------
   Paged Media Adjustments
   -------------------------------------------------------------------------- */
@page {
  margin: 18mm 14mm 22mm 14mm;
}

/* Page 1 Margin Adjustment */
@page:first {
  margin-top: 18mm;
}
```

---

### 4.2 Patch 2: `styles/base/paged.css`

#### Target File
`/home/valor/Devel/personal/md-style/styles/base/paged.css` (Section 3 lines 45–51, and Section 8 lines 190–193)

#### Proposed Unified Diff
```diff
--- a/styles/base/paged.css
+++ b/styles/base/paged.css
@@ -44,6 +44,19 @@
   page-break-inside: avoid !important;
 }
 
+/* Universal component break-inside avoidance across all themes */
+.signature-block,
+.signature-line,
+.signature-row,
+.committee-signature,
+.sign-off,
+.callout,
+.admonition,
+.kpi-card,
+.kpi-grid,
+figure {
+  break-inside: avoid !important;
+  page-break-inside: avoid !important;
+}
+
 h1, h2, h3, h4, h5, h6,
 .agenda-heading {
   break-after: avoid !important;
@@ -188,7 +201,10 @@
     break-inside: avoid !important;
   }
 
-  tr, li, blockquote, .callout, figure, pre {
+  tr, li, blockquote, .callout, .admonition, figure, pre,
+  .signature-block, .signature-line, .signature-row,
+  .committee-signature, .sign-off, .kpi-card, .kpi-grid {
     break-inside: avoid !important;
+    page-break-inside: avoid !important;
   }
 
   h1, h2, h3, h4, h5, h6 {
```

#### Code Snippet (Before vs After)
**Section 3 After**:
```css
/* --------------------------------------------------------------------------
   3. Break Protection & Stacking Contexts (Structural Layout Fixes)
   -------------------------------------------------------------------------- */
/* Orphan, widow, heading and list item break protection across all themes */
p {
  orphans: 3;
  widows: 3;
}

li {
  break-inside: avoid !important;
  page-break-inside: avoid !important;
}

/* Universal component break-inside avoidance across all themes */
.signature-block,
.signature-line,
.signature-row,
.committee-signature,
.sign-off,
.callout,
.admonition,
.kpi-card,
.kpi-grid,
figure {
  break-inside: avoid !important;
  page-break-inside: avoid !important;
}

h1, h2, h3, h4, h5, h6,
.agenda-heading {
  break-after: avoid !important;
  page-break-after: avoid !important;
}
```

**Section 8 (`@media print`) After**:
```css
  tr, li, blockquote, .callout, .admonition, figure, pre,
  .signature-block, .signature-line, .signature-row,
  .committee-signature, .sign-off, .kpi-card, .kpi-grid {
    break-inside: avoid !important;
    page-break-inside: avoid !important;
  }
```

---

### 4.3 Patch 3: `styles/base/print.css`

#### Target File
`/home/valor/Devel/personal/md-style/styles/base/print.css` (Lines 50–60)

#### Proposed Unified Diff
```diff
--- a/styles/base/print.css
+++ b/styles/base/print.css
@@ -55,6 +55,16 @@
 div.tip,
 div.important,
 div.caution,
-div.critical {
+div.critical,
+.callout,
+.admonition,
+figure,
+.signature-block,
+.signature-line,
+.signature-row,
+.committee-signature,
+.sign-off,
+.kpi-card,
+.kpi-grid {
   break-inside: avoid !important;
   page-break-inside: avoid !important;
 }
```

#### Code Snippet (Before vs After)
**Before**:
```css
.proposal-callout,
blockquote,
div.note,
div.warning,
div.tip,
div.important,
div.caution,
div.critical {
  break-inside: avoid !important;
  page-break-inside: avoid !important;
}
```

**After**:
```css
.proposal-callout,
blockquote,
div.note,
div.warning,
div.tip,
div.important,
div.caution,
div.critical,
.callout,
.admonition,
figure,
.signature-block,
.signature-line,
.signature-row,
.committee-signature,
.sign-off,
.kpi-card,
.kpi-grid {
  break-inside: avoid !important;
  page-break-inside: avoid !important;
}
```

---

## 5. Verification Method

### Step 1: Verification of Duplicate Page Number Removal
1. Compile the SVJ invitation sample document:
   ```bash
   uv run md-style "examples/pozvánka-shromáždění-svj.md" -s svj/invitation -p -o output/pozvanka-svj.pdf
   ```
2. Extract page 2 text using `/usr/bin/pdftotext`:
   ```bash
   pdftotext -f 2 -l 2 output/pozvanka-svj.pdf - | tail -n 8
   ```
3. **Success assertion**:
   The output must contain:
   ```text
   Statutární orgán / Výbor SVJ    Dle § 1207 z. č. 89/2012 Sb. (občanský zákoník)
   Strana 2 z 5
   ```
   and MUST NOT contain the bare isolated digit `2` preceding `Strana 2 z 5`.

### Step 2: Verification of Break-Inside Protection
1. Compile documents featuring signature blocks, callouts, and KPI grids:
   ```bash
   uv run md-style examples/school-report-sample.md -s general/school -p -o output/school-report.pdf
   uv run md-style examples/sample-forensic-cyber.md -s forensic/cyber -p -o output/sample-forensic-cyber.pdf
   ```
2. Inspect bounding boxes of `.signature-block` in `output/school-report.pdf` using `pdftotext -bbox-layout`:
   ```bash
   pdftotext -bbox-layout output/school-report.pdf - | grep -B 2 -A 5 "Dr. Eleanor Vance"
   ```
   Verify that all signature lines remain together on the final page without splitting.

### Step 3: Run Full Regression Suite
Run all unit and integration tests to ensure 0 regressions:
```bash
uv run pytest tests/ -k "not e2e" -v
```
Expected result: 162 passed in ~20 seconds.

### Invalidation Conditions
- Any occurrence of both a bare page number and a formatted string (e.g. `2` and `Strana 2 z 5`) on page 2 of `output/pozvanka-svj.pdf`.
- Any split of a `.signature-block`, `.callout`, `.kpi-card`, or `figure` across consecutive PDF pages.
- Failure of any of the 162 existing tests.
