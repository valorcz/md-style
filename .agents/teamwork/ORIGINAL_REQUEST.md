# Original User Request

## 2026-10-11T10:15:11Z

Perform a comprehensive architectural audit, headless browser end-to-end testing hardening, and print fidelity verification for the `md-style` document publishing and interactive viewer system.

Working directory: /home/valor/Devel/personal/md-style
Integrity mode: demo

## Requirements

### R1. End-to-End Headless Browser Interactivity Test Suite
Build an automated, reproducible end-to-end browser test suite (using Playwright or Puppeteer) verifying the interactive Svelte Viewer runtime:
- Text selection, annotation creation, live Markdown preview, and storage persistence across reloads.
- Tag and category filtering in the slide-over Inspector Drawer (`InspectorDrawer.svelte`).
- Table search, column filtering, and category pill interactions (`TableToolbar.svelte`).
- Clean bundle export (`exportUpdatedHtmlBundle`) ensuring downloaded HTML files re-hydrate without DOM pollution or duplicated UI elements.
- Interaction disambiguation between `.inspectable` pills and text selection.

### R2. W3C Paged Media & Vector PDF Print Fidelity Verification
Create an automated verification harness for print output across all themes (`styles/forensic/`, `styles/svj/`, `styles/general/`):
- Verify that running headers, running footers, and page numbers (`Page X of Y`) render accurately without overlapping or truncation in both Chromium CDP vector PDF export and in-browser Paged.js preview.
- Ensure page-break avoidance rules (`break-inside: avoid` / `page-break-inside: avoid`) hold for tables, diagram figures, callouts, and signature blocks across page boundary splits.
- Verify ordered list item counter continuation across multi-page boundaries.

### R3. Comprehensive Pipeline Architectural Audit & Hardening
Audit the modular compilation pipeline (`core/engine.py`, `core/bundler.py`, `core/parser/`, `core/kb/`):
- Verify zero runtime external network requests across all themes and bundled deliverables (air-gap strictness).
- Verify resilience against malformed inputs (invalid frontmatter, deeply nested Pandoc callouts, unmatched fenced blocks).
- Ensure consistent cross-platform exit codes, deterministic terminal diagnostics, and accurate build timing metrics.

## Acceptance Criteria

### Headless E2E Browser Testing
- [ ] Automated test suite runs via a single command (e.g. `npm test` or `uv run pytest tests/e2e/`) and completes in headless mode.
- [ ] Tests verify annotation creation, editing, deletion with tombstones, and re-hydration from both `localStorage` and embedded script tags.
- [ ] Tests verify that exported updated HTML bundles re-open with zero console errors and full annotation visibility.

### Print & Paged Media Fidelity
- [ ] Verification script compiles sample documents across forensic, SVJ, and school themes to PDF.
- [ ] Automated PDF inspection verifies that page numbers increment monotonically (`1 of N` to `N of N`) and headers match document metadata.
- [ ] Automated check confirms zero orphan headers or split table headers across page breaks.

### Pipeline Integrity & Robustness
- [ ] Offline test confirms 0 external network requests during compilation and viewer execution.
- [ ] All existing 87 unit tests continue to pass with 0 regressions.
- [ ] Audit report document summarizing findings, identified vulnerabilities or edge cases, and implemented fixes is produced in `docs/`.
