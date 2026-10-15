# Project: md-style Architectural Audit, Headless E2E, and Print Fidelity Verification

## Architecture
- **Compilation Engine**: Pure-Python modular pipeline (`core/engine.py`, `core/bundler.py`, `core/parser/`, `core/kb/`).
- **Styles & Themes**: W3C Paged Media stylesheets (`styles/base/`, `styles/forensic/`, `styles/svj/`, `styles/general/`).
- **Interactive Svelte Viewer**: Client-side reactive bundle (`viewer/src/`, `core/assets/viewer.bundle.js`).
- **Print Export**: Headless Chromium CDP vector printer (`viewer/scripts/print-pdf.mjs`).
- **Test Frameworks**: `pytest` for unit/offline/print tests, `pytest-playwright` for headless browser E2E tests.

## Feature Inventory
| # | Feature | Description | Milestone | Source |
|---|---------|-------------|-----------|--------|
| 1 | Air-gap strictness (IP resolver) | Guard reverse DNS lookups behind `allow_online` | M1 | Survey 3 |
| 2 | Air-gap strictness (Fonts) | Support `allow_online=False` in `FontBundler`, prevent Google Fonts fetch on cold cache | M1 | Survey 3 |
| 3 | Air-gap strictness (Icons) | Support `allow_online=False` in `IconService`, prevent GitHub CDN fetch | M1 | Survey 3 |
| 4 | Offline air-gap test harness | Intercept sockets to assert 0 external WAN network calls | M1 | Survey 3 |
| 5 | Callout parser nesting | Recursively parse nested blockquote alerts (`> [!NOTE] > > [!WARNING]`) | M1 | Survey 3 |
| 6 | Callout title deduplication | Strip extracted title from single-line alert body content | M1 | Survey 3 |
| 7 | CLI exit code determinism | Raise `RuntimeError` on failed PDF compilation so CLI exits with code 1 | M1 | Survey 3 |
| 8 | Build timing diagnostics | Add structured 5-stage timing breakdown in verbose mode; fix stage 1 timer | M1 | Survey 3 |
| 9 | Highlight style default | Change `PipelineConfig.highlight_style` default from `"kate"` to `None` | M1 | Survey 3 |
| 10 | 87 unit tests regression guard | Guarantee all 87 baseline tests in `tests/` pass with 0 regressions | M1 | Survey 3 |
| 11 | Duplicate SVJ page number fix | Remove `@bottom-right { content: counter(page); }` from `styles/svj/invitation/invitation.css` | M2 | Survey 2 |
| 12 | Forensic leaks in general themes | Restrict `_should_build_dossier_header()` and forensic badges to forensic themes | M2 | Survey 2 |
| 13 | Forensic PDF footer fingerprint | Pass `bundler.fingerprint` to `build_cdp_header_footer_templates()` | M2 | Survey 2 |
| 14 | Universal break-inside rules | Add `.signature-block`, `.callout`, `.kpi-card`, `figure` to base paged and print CSS | M2 | Survey 2 |
| 15 | Automated print verification | Create `tests/test_print_fidelity.py` inspecting bounding boxes and page numbers via `pdftotext -bbox-layout` | M2 | Survey 2 |
| 16 | Makefile sample PDF target | Add `examples/school-report-sample.md` to `samples-pdf` in `Makefile` | M2 | Survey 2 |
| 17 | Playwright E2E configuration | Configure headless Playwright with system `/usr/bin/chromium-browser` in `tests/e2e/conftest.py` | M3 | Survey 1 |
| 18 | TableToolbar E2E tests | Verify category pills, live search, row hiding, and count badge | M3 | Survey 1 |
| 19 | InspectorDrawer E2E tests | Verify entity drawer opening, entity search, category filtering, and review tab | M3 | Survey 1 |
| 20 | Interaction disambiguation E2E | Verify text selection across `.inspectable` pills suppresses drawer opening and shows popover | M3 | Survey 1 |
| 21 | Annotation lifecycle & preview E2E | Verify text selection, category tagging, live Markdown preview tab, and saving | M3 | Survey 1 |
| 22 | Storage persistence & tombstones E2E | Verify persistence across reload, card editing, and tombstone deletion | M3 | Survey 1 |
| 23 | Script tag re-hydration E2E | Verify re-hydration from `#md-style-annotations` and tombstone override | M3 | Survey 1 |
| 24 | Clean bundle export E2E | Verify `exportUpdatedHtmlBundle` unwraps marks, strips transient roots, and re-opens with 0 console errors | M3 | Survey 1 |
| 25 | Comprehensive Audit Report | Write `docs/pipeline_audit_report.md` covering architecture, air-gap, resilience, metrics | M4 | Survey 3 |
| 26 | Documentation updates | Update `docs/architecture.md` and related docs for Pure-Python v3 pipeline | M4 | Survey 3 |
| 27 | Full acceptance suite verification | Run all unit tests, offline test, print test, and E2E tests with 0 failures | M4 | Survey 1, 2, 3 |

## Milestones
| # | Name | Scope | Dependencies | Status |
|---|------|-------|-------------|--------|
| M1 | Pipeline Hardening & Air-Gap Enforcement (R3) | Fix IP resolver, fonts, icons, bundler, callouts, exit codes; create `tests/test_airgap_offline.py`; verify 87 baseline tests | none | DONE |
| M2 | Print Fidelity & Theme Fixes (R2) | Fix SVJ duplicate page numbers, forensic theme leaks, fingerprint footer, break rules; create `tests/test_print_fidelity.py` | M1 | DONE |
| M3 | Headless Browser E2E Test Suite (R1) | Configure Playwright, build `tests/e2e/test_svelte_viewer.py` verifying all 8 interactive scenarios; update Makefile | M1, M2 | PLANNED |
| M4 | Final Acceptance & Documentation Audit (AC) | Execute all test suites (87 unit + offline + print + E2E); create `docs/pipeline_audit_report.md` and update docs | M1, M2, M3 | PLANNED |

## Interface Contracts
### `ReportEngine` ↔ `AssetBundler` ↔ `FontBundler` / `IconService`
- `PipelineConfig`: `allow_online: bool` defaults to `True`, set to `False` by `--offline`.
- `AssetBundler(config=..., allow_online=bool)` forwards `allow_online` to `FontBundler(allow_online=bool)` and `IconService(allow_online=bool)`.
- When `allow_online=False`:
  - `FontBundler.fetch_css_import()` returns `None` without network I/O.
  - `FontBundler.fetch_font_binary()` returns `None` without network I/O.
  - `IconService.get_svg()` skips GitHub CDN and returns fallback SVG.
  - `IpResolver.resolve()` skips `_resolve_ptr()` if `allow_online=False`.

### `ReportEngine` ↔ `_compile_pdf`
- `_compile_pdf(source_html: Path, destination_pdf: Path, theme: Theme, ...)`:
  - If CDP printer fails and fallback browsers fail, MUST raise `RuntimeError("PDF export failed: ...")`.
  - Must pass `fingerprint=bundler.fingerprint` to `bundler.build_cdp_header_footer_templates(...)`.

### `ReportEngine` ↔ `_should_build_dossier_header`
- Dossier badge and examiner label MUST only activate for themes where `"forensic" in style.lower()`.
- Non-forensic themes with frontmatter author/date receive standard metadata blocks without "FORENSIC INVESTIGATION REPORT" or "Examiner:".

## Code Layout
- `core/engine.py`: Compilation pipeline, timing metrics, PDF export bridge, dossier header logic.
- `core/bundler.py`: Asset inlining, script injection, CDP options building.
- `core/fonts.py`: Font bundling, Google Fonts fetching.
- `core/icons.py`: Octicons and custom SVG resolution.
- `core/kb/resolvers/ip_resolver.py`: IP entity resolution and PTR lookups.
- `core/parser/plugins/callouts.py`: GitHub alert blockquote parsing and rendering.
- `styles/base/paged.css`: Base paged media stylesheet and break rules.
- `styles/base/print.css`: Print stylesheet and fragmentation rules.
- `styles/svj/invitation/invitation.css`: SVJ invitation theme styles.
- `tests/test_airgap_offline.py`: Socket interception air-gap tests.
- `tests/test_print_fidelity.py`: PDF compilation and XML layout inspection tests.
- `tests/e2e/conftest.py`: Playwright fixtures with `/usr/bin/chromium-browser`.
- `tests/e2e/test_svelte_viewer.py`: Headless browser E2E test suite.
- `docs/pipeline_audit_report.md`: Formal architectural and integrity audit report.
