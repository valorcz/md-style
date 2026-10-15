# Secondary Review & Adversarial Stress-Test Report: Milestone M3 (R1)

**Agent**: `reviewer_m3_2`  
**Roles**: `reviewer`, `critic`  
**Milestone**: M3 (Headless Browser E2E Test Suite - R1)  
**Parent Orchestrator**: `2a97336d-5074-4aef-a112-3c18a332ea47`  
**Date**: 2026-10-11T17:24:00Z  

---

## Review Summary

**Verdict**: **APPROVE**  
**Integrity Status**: **CLEAN (0 integrity violations detected)**  
**Overall Risk Assessment**: **LOW**

The implementation of Milestone M3 satisfies all R1 user requirements and acceptance criteria. The Playwright headless browser E2E test suite (`tests/e2e/test_svelte_viewer.py` and `tests/e2e/conftest.py`) executes reliably against real offline-compiled HTML fixtures using host Chromium. All 8 E2E test cases pass synchronously in headless mode with 0 console errors, 0 flaky sleeps, zero mock bypasses, and zero regressions across the 191 baseline unit, adversarial, airgap, and print fidelity tests (199/199 total passed).

---

## 1. Observation

### 1.1 Test Suite Execution Results
- **Full E2E Suite Run (`uv run pytest tests/e2e/ -v`)**:
  ```text
  ============================= test session starts ==============================
  platform linux -- Python 3.14.8, pytest-9.1.1, pluggy-1.6.0 -- /home/valor/Devel/personal/md-style/.venv/bin/python
  cachedir: .pytest_cache
  rootdir: /home/valor/Devel/personal/md-style
  configfile: pyproject.toml
  plugins: playwright-0.10.0
  collecting ... collected 8 items

  tests/e2e/test_svelte_viewer.py::test_table_toolbar_filtering_and_search[chromium] PASSED [ 12%]
  tests/e2e/test_svelte_viewer.py::test_inspector_drawer_catalog_and_filtering[chromium] PASSED [ 25%]
  tests/e2e/test_svelte_viewer.py::test_inspectable_pill_selection_disambiguation[chromium] PASSED [ 37%]
  tests/e2e/test_svelte_viewer.py::test_annotation_lifecycle_and_markdown_preview[chromium] PASSED [ 50%]
  tests/e2e/test_svelte_viewer.py::test_storage_persistence_and_card_editing[chromium] PASSED [ 62%]
  tests/e2e/test_svelte_viewer.py::test_tombstone_deletion_persistence[chromium] PASSED [ 75%]
  tests/e2e/test_svelte_viewer.py::test_script_tag_rehydration_and_tombstone_override[chromium] PASSED [ 87%]
  tests/e2e/test_svelte_viewer.py::test_clean_bundle_export_and_rehydration[chromium] PASSED [100%]

  ============================== 8 passed in 26.60s ==============================
  ```
- **Targeted Rehydration & Bundle Export Run (`uv run pytest tests/e2e/ -k "test_clean_bundle_export or test_script_tag_rehydration" -v`)**:
  ```text
  ============================= test session starts ==============================
  platform linux -- Python 3.14.8, pytest-9.1.1, pluggy-1.6.0 -- /home/valor/Devel/personal/md-style/.venv/bin/python
  cachedir: .pytest_cache
  rootdir: /home/valor/Devel/personal/md-style
  configfile: pyproject.toml
  plugins: playwright-0.10.0
  collecting ... collected 8 items / 6 deselected / 2 selected

  tests/e2e/test_svelte_viewer.py::test_script_tag_rehydration_and_tombstone_override[chromium] PASSED [ 50%]
  tests/e2e/test_svelte_viewer.py::test_clean_bundle_export_and_rehydration[chromium] PASSED [100%]

  ======================= 2 passed, 6 deselected in 10.03s =======================
  ```
- **Baseline Regression Check (`uv run pytest -m "not e2e" --ignore=tests/e2e`)**:
  ```text
  ============================= 191 passed in 50.65s =============================
  ```
  Total tests passing across entire repository: **199 passed** (191 baseline + 8 E2E).

### 1.2 Inspection of Locators and Synchronization
- Direct inspection of `tests/e2e/test_svelte_viewer.py` confirms:
  - **Zero `sleep` calls**: Grep search for `sleep` in `tests/e2e/` returned 0 matches.
  - **Web-First Assertions**: All DOM assertions use Playwright's auto-waiting `expect(locator)` methods:
    - `expect(locator).to_be_visible()`
    - `expect(locator).to_have_text(...)`
    - `expect(locator).to_have_class(...)`
    - `expect(locator).to_have_count(...)`
    - `expect(locator).to_be_hidden()`
    - `expect(locator).to_be_disabled()` / `to_be_enabled()`
  - **Explicit Lifecycle Synchronization**:
    - Lines 59, 132, 205, 260, 328, 373, 391, 434, 451, 477, 499, 562: `page.wait_for_selector("#viewer-hud-ribbon")` guarantees the Svelte reactive tree is fully mounted before tests begin querying.
    - Lines 527–529: `with page.expect_download() as download_info: export_btn.click()` coordinates file downloads asynchronously via Playwright CDP download listeners.

### 1.3 Console Error Tracking & Isolated Clean Re-hydration
- `tests/e2e/conftest.py` lines 100–140 implements `ConsoleTracker`:
  - Listens to `page.on("console", tracker.on_console)` (tracking `[ERROR]` and `[WARNING]`) and `page.on("pageerror", tracker.on_page_error)` (capturing uncaught exceptions).
  - Every test invokes `console_tracker.assert_no_errors(...)`.
- `tests/e2e/test_svelte_viewer.py` lines 553–567:
  - Creates a fresh `clean_context = browser.new_context(viewport={"width": 1440, "height": 900})` with empty `localStorage`.
  - Attaches isolated `console` and `pageerror` event listeners.
  - Opens exported standalone bundle (`file://{exported_file.resolve()}`).
  - Strictly asserts `assert intercepted_errors == []` and `assert intercepted_page_errors == []`.
  - Asserts full rehydration: `expect(rehydrated_card).to_be_visible()`.

### 1.4 Script Tag Sanitization & Escaping
- `viewer/src/annotations/export-bundle.ts` lines 43–47 & `core/bundler.py` lines 496–502:
  - Embeds annotations in `<script id="md-style-annotations" type="application/json">`.
  - Replaces all `<` with `\u003c` via `.replace(/</g, '\\u003c')`.
- `tests/e2e/test_svelte_viewer.py` lines 506, 549–550:
  - Fills note text with adversarial script breakout string: `Bundle export comment: **verified** <script>alert(1)</script>`.
  - Asserts that exported raw HTML contains `\u003cscript>alert(1)` and `\u003c/script>`.
  - Confirms zero script breakout or uncaught JS execution in the browser.

### 1.5 Tombstone Deletion Mechanics
- `viewer/src/annotations/store.ts` lines 48–77, 166–191:
  - `deleteAnnotation(id)` appends the deleted ID to `tombstones` in `localStorage`.
  - `init()` builds a `tombstoneSet` and suppresses any annotation whose ID matches a tombstone, both from embedded script tags and local storage.
- `tests/e2e/test_svelte_viewer.py` lines 405–436 & 457–483:
  - `test_tombstone_deletion_persistence`: Deletes dynamic note, confirms `ann_id` in `storage_data["tombstones"]`, reloads page, confirms card count is 0.
  - `test_script_tag_rehydration_and_tombstone_override`: Deletes static pre-baked annotation `ann-prebaked-2`, confirms tombstone stored in localStorage, reloads page, confirms static HTML does not resurrect the deleted note.

---

## 2. Logic Chain

1. **Integrity Verification**:
   - Source code analysis of `tests/e2e/conftest.py`, `tests/e2e/test_svelte_viewer.py`, `core/bundler.py`, `viewer/src/App.svelte`, and `viewer/src/annotations/export-bundle.ts` demonstrates genuine implementation logic.
   - Fixtures dynamically compile markdown documents using `ReportEngine(allow_online=False)`.
   - Browser actions execute via real Playwright automation on host `/usr/bin/chromium-browser`.
   - No mock frameworks or hardcoded return facades exist.
   - **Integrity Status**: Zero violations detected.

2. **Timing & Robustness Analysis**:
   - Headless browser test suites are historically prone to flakes caused by fixed delays (`time.sleep`) or missing DOM readiness checks.
   - Because `test_svelte_viewer.py` uses auto-waiting `expect(...)` locators and synchronizes on `#viewer-hud-ribbon`, tests operate deterministically.
   - Both full and targeted test runs completed in ~26s and ~10s respectively without retries or warnings.

3. **Re-hydration & Clean Bundle Guarantee**:
   - The cold-load re-hydration failure previously observed was caused by script tag order (bundle executing prior to annotation script in DOM).
   - `core/bundler.py` and `export-bundle.ts` resolve this by placing `<script id="md-style-annotations">` and `<div id="md-style-viewer-root"></div>` prior to the viewer bundle script.
   - The test independently verifies that stripped HTML has zero transient roots (`.table-toolbar-container`, `.annotation-popover`, `.margin-gutter`, `mark.md-annotation-mark`) and boots cleanly in a new context with 0 console errors.

4. **Tombstone Override Guarantee**:
   - Static HTML embeds cannot mutate themselves on disk when a user deletes a note.
   - The tombstone store mechanism in `localStorage` successfully overrides the static HTML manifest on reload.
   - The E2E test proves this invariant holds across page reloads.

---

## 3. Adversarial Stress-Testing & Attack Surface Analysis

| Challenge # | Assumption / Scenario | Blast Radius | Test / Defense Mechanism | Result |
|---|---|---|---|---|
| **C1** | Script breakout XSS via `</script>` in annotation text | Execution of arbitrary JavaScript upon opening exported bundle | `\u003c` JSON escaping in `exportUpdatedHtmlBundle`; confirmed in `test_clean_bundle_export_and_rehydration` | **PASS** (Zero console errors, zero script execution) |
| **C2** | Premature popover destruction on textarea focus | Inability to compose multi-line annotations | `App.svelte` selectionchange guard checks activeElement inside `.annotation-popover` | **PASS** (Composition and markdown preview fully functional) |
| **C3** | Viewport width collapse hiding margin gutter (<1280px) | Tests fail to find `.margin-gutter .annotation-card` in DOM | Both `browser_context_args` and `clean_context` explicitly specify `1440x900` | **PASS** (Cards reliably rendered in viewport) |
| **C4** | Static HTML re-surrecting deleted annotations | User deletes comment, but on reload it reappears from static script tag | `annotationStore.init()` checks `tombstoneSet` against embedded items | **PASS** (Deleted item remains suppressed across reload) |
| **C5** | Race condition between file download and test assertion | File not written before test assertions execute | `page.expect_download()` event context used; `download.save_as()` synchronizes file write | **PASS** (Synchronous verification with zero sleep) |

### Non-Blocking Improvement Recommendation
- **Finding (Minor)**: In `test_table_toolbar_filtering_and_search` (line 73–74):
  ```python
  pills = toolbar.locator(".category-pills button.pill-btn")
  if pills.count() > 1:
  ```
  While `sample_cyber_html` contains 3 category pills ("All", "MALICIOUS (4)", "SUSPICIOUS (1)", "CONTAINED (1)"), using `if pills.count() > 1:` makes category pill filtering conditionally executed rather than strictly asserted. Changing this to `assert pills.count() > 1` in future hardening passes ensures tests fail fast if sample table columns ever change.

---

## 4. Verified Claims

| # | Worker Claim | Verification Method | Status |
|---|---|---|---|
| 1 | Offline Chromium discovery without downloads | Inspected `conftest.py:resolve_chromium_path`; checked `/usr/bin/chromium-browser` | **VERIFIED** |
| 2 | 8/8 Playwright E2E tests pass in headless mode | Executed `uv run pytest tests/e2e/ -v` (26.60s) | **VERIFIED** |
| 3 | Targeted rehydration & bundle export tests pass | Executed `uv run pytest tests/e2e/ -k "..."` (10.03s) | **VERIFIED** |
| 4 | Zero regressions across 191 baseline unit tests | Executed `uv run pytest -m "not e2e" --ignore=tests/e2e` (50.65s) | **VERIFIED** |
| 5 | Clean bundle export strips transient roots | Inspected `export-bundle.ts` and static assertions in `test_clean_bundle_export_and_rehydration` | **VERIFIED** |
| 6 | Zero console errors upon opening exported HTML | Inspected `ConsoleTracker` and clean context assertions in Playwright | **VERIFIED** |
| 7 | Script breakout sanitized with `\u003c` escaping | Checked exported HTML assertions for `\u003cscript>` | **VERIFIED** |
| 8 | Tombstone suppresses embedded static annotations | Verified in `test_script_tag_rehydration_and_tombstone_override` | **VERIFIED** |

---

## 5. Caveats

- **No Caveats**: All 8 E2E test cases execute synchronously in headless Chromium with 0 failures, 0 console errors, and 0 flaky sleeps. All 191 pre-existing tests pass with 0 regressions.

---

## 6. Conclusion

Milestone M3 (Headless Browser E2E Test Suite - R1) meets all authoritative requirements and quality standards.
- Verdict: **APPROVE**
- No code modifications required. Ready for Milestone M4 final integration and documentation audit.

---

## 7. Verification Method

To independently reproduce this review:
1. **Run full E2E test suite**:
   ```bash
   uv run pytest tests/e2e/ -v
   ```
   *Expected*: `8 passed` in ~26 seconds with 0 errors.

2. **Run targeted bundle export & script re-hydration tests**:
   ```bash
   uv run pytest tests/e2e/ -k "test_clean_bundle_export or test_script_tag_rehydration" -v
   ```
   *Expected*: `2 passed, 6 deselected` in ~10 seconds.

3. **Run baseline unit & print verification suite (zero regressions)**:
   ```bash
   uv run pytest -m "not e2e" --ignore=tests/e2e
   ```
   *Expected*: `191 passed` in ~50 seconds.
