# Independent Review & Adversarial Stress Report: Milestone M3 (Headless Browser E2E Test Suite - R1)

**Reviewer**: `reviewer_m3_1` (Roles: `reviewer`, `critic`)  
**Date**: 2026-10-11T17:21:00Z  
**Milestone**: M3 (Headless Browser E2E Test Suite - R1)  
**Parent Orchestrator**: `2a97336d-5074-4aef-a112-3c18a332ea47`  
**Verdict**: **APPROVE**

---

## 1. Observation

### 1.1 Test Suite Execution
Direct execution of both test suites produced the following verbatim terminal outputs:

- **E2E Headless Browser Test Suite (`uv run pytest tests/e2e/ -v`)**:
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

  ============================== 8 passed in 26.49s ==============================
  ```

- **Full Project Regression Test Suite (`uv run pytest`)**:
  ```text
  ============================= test session starts ==============================
  platform linux -- Python 3.14.8, pytest-9.1.1, pluggy-1.6.0
  rootdir: /home/valor/Devel/personal/md-style
  configfile: pyproject.toml
  plugins: playwright-0.10.0
  collecting ... collected 199 items

  tests/e2e/test_svelte_viewer.py ........                                 [  4%]
  tests/test_airgap_adversarial.py .....................                   [ 14%]
  tests/test_airgap_offline.py ............                                [ 20%]
  tests/test_bundler.py .                                                  [ 21%]
  tests/test_callout_adversarial_stress.py .............................   [ 35%]
  tests/test_callout_plugin.py ...........                                 [ 41%]
  tests/test_cleanup.py ..                                                 [ 42%]
  tests/test_cwe_resolver.py ....                                          [ 44%]
  tests/test_d2_diagrams.py ....                                           [ 46%]
  tests/test_diagrams.py .....                                             [ 48%]
  tests/test_engine_diagnostics.py .......                                 [ 52%]
  tests/test_font_bundling.py .                                            [ 52%]
  tests/test_i18n.py .....                                                 [ 55%]
  tests/test_icons.py ..                                                   [ 56%]
  tests/test_kb_lifecycle.py .....                                         [ 58%]
  tests/test_kb_resolvers.py ...............                               [ 66%]
  tests/test_loaders.py ..                                                 [ 67%]
  tests/test_paged_theme.py ...........                                    [ 72%]
  tests/test_pandoc_compat.py .....                                        [ 75%]
  tests/test_parser.py ....                                                [ 77%]
  tests/test_print_fidelity.py .....................                       [ 87%]
  tests/test_print_fidelity_adversarial.py ........                        [ 91%]
  tests/test_pygments_highlighting.py ...                                  [ 93%]
  tests/test_style_remediation.py ..........                               [ 98%]
  tests/test_themes.py ...                                                 [100%]

  ======================== 199 passed in 77.10s (0:01:17) ========================
  ```

### 1.2 Configuration & Build Tooling
- **`pyproject.toml`** (lines 29–34):
  ```toml
  [dependency-groups]
  dev = [
      "pytest>=8.4.2",
      "playwright>=1.40.0",
      "pytest-playwright>=0.5.0",
  ]
  ```
- **`Makefile`** (lines 27–32):
  ```makefile
  test:
  	uv run pytest -v

  test-e2e:
  	uv run pytest tests/e2e/ -v
  ```

### 1.3 Code Implementations & Bug Fixes
- **`tests/e2e/conftest.py`**:
  - `resolve_chromium_path()` (lines 20–58) probes `CHROME_BIN`, `shutil.which` (`chromium-browser`, `chromium`, `google-chrome`), canonical Linux locations (`/usr/bin/chromium-browser`, `/snap/bin/chromium`), and `~/.cache/ms-playwright`.
  - `browser_type_launch_args` (lines 61–80) configures `headless=True` and sandbox-resilient flags (`--no-sandbox`, `--disable-dev-shm-usage`, `--headless=new`).
  - `browser_context_args` (lines 83–97) enforces desktop viewport `1440x900` (exceeding the `1280px` responsive breakpoint in `MarginGutter.svelte`) and `accept_downloads=True`.
  - `ConsoleTracker` (lines 100–140) hooks `page.on("console")` and `page.on("pageerror")` to capture uncaught errors and logs.
  - `sample_cyber_html` and `sample_annotated_html` compile fixtures with `PipelineConfig(allow_online=False, highlight_style=None)`.
- **`viewer/src/App.svelte`** (lines 288–291):
  Fixed popover premature unmounting when the composer gains focus:
  ```ts
  const popover = document.querySelector('.annotation-popover');
  if (popover && (popover.contains(document.activeElement) || popover.querySelector('.popover-composer'))) {
    return;
  }
  ```
- **`core/bundler.py`** & **`viewer/src/annotations/export-bundle.ts`**:
  - `bundler.py` places `<script id="md-style-annotations">` before `<div id="md-style-viewer-root"></div>` and the viewer script block inside `<body>`, ensuring script tag re-hydration happens synchronously before viewer initialization.
  - `export-bundle.ts` escapes `<` characters as `\u003c` in exported JSON, prevents duplicate mount roots via `clone.querySelectorAll('#md-style-viewer-root').forEach(el => el.remove())`, and strips transient classes (`.table-toolbar-container`, `.annotation-popover`, `.margin-gutter`, `.md-annotation-mark`).

---

## 2. Logic Chain

1. **R1 Requirement Conformance**:
   - *Text selection & popover*: `test_annotation_lifecycle_and_markdown_preview` programmatically selects text within `.report-content`, verifies `.annotation-popover` appears, tests category tagging, ensures the save button is disabled when empty, verifies live markdown rendering in the Preview tab (`<strong>`, `<code>`), and asserts `.margin-gutter .annotation-card` and HUD ribbon count updates.
   - *Inspector drawer search & category filtering*: `test_inspector_drawer_catalog_and_filtering` opens the drawer via HUD ribbon, verifies `body.inspector-open`, performs live search (`CVE-`), tests category pills (`CVE`), navigates to single entity hero card, returns via back button, and closes the drawer.
   - *TableToolbar filtering & count badge*: `test_table_toolbar_filtering_and_search` discovers categorical columns, tests category pills, verifies `.count-badge` updating (`visible / total`), tests live search input with matching rows, and verifies clear button reset.
   - *Clean bundle export & zero console errors*: `test_clean_bundle_export_and_rehydration` exports an updated bundle with embedded annotations (including XSS test characters `<script>alert(1)</script>`), verifies static removal of transient UI elements and `<` -> `\u003c` escaping, and re-opens the file in a fresh isolated browser context with zero console errors, zero uncaught page errors, and full card visibility.
   - *Interaction disambiguation*: `test_inspectable_pill_selection_disambiguation` verifies that clean click on `.inspectable` opens the entity drawer, whereas click during active text selection across `.inspectable` suppresses drawer opening and keeps the annotation popover open.
   - *Script tag re-hydration & tombstone override*: `test_script_tag_rehydration_and_tombstone_override` verifies re-hydration from `#md-style-annotations` on cold start and proves local storage tombstones override and suppress embedded items across page reloads.

2. **Integrity & Anti-Cheat Audit**:
   - Checked source code in `tests/e2e/test_svelte_viewer.py` and `tests/e2e/conftest.py` for hardcoded return values, mocks, facade implementations, or bypassed assertions.
   - All tests interact with live Chromium instances, dispatch genuine DOM events, inspect actual computed styles and element visibility, and query real `localStorage`.
   - No mock libraries or external proxies are used; all tests run 100% offline with zero external network requests.
   - Test execution results were generated independently during this review and verified to match.

3. **Zero Regression Verification**:
   - Running the full test suite (`uv run pytest`) confirmed 199 tests passed (191 pre-existing unit/offline/print tests + 8 new E2E tests) with zero failures or regressions.

---

## 3. Caveats & Adversarial Findings

### 3.1 Adversarial Stress Observations
1. **[Minor / Non-blocking] `rootEl` Placement in `export-bundle.ts`**:
   - In `viewer/src/annotations/export-bundle.ts` line 55:
     ```ts
     if (!clone.querySelector('#md-style-viewer-root')) {
       const rootEl = document.createElement('div');
       rootEl.id = 'md-style-viewer-root';
       clone.appendChild(rootEl);
     }
     ```
     `clone` is `document.documentElement` (`<html>`). Appending `rootEl` appends the `div` as a direct child of `<html>` instead of `<body>`. While Chromium’s HTML parser normalizes this by hoisting the `div` into `<body>` upon parsing (verified by zero console errors in `test_clean_bundle_export_and_rehydration`), it is recommended to use `(clone.querySelector('body') || clone).appendChild(rootEl)` for standard DOM hierarchy compliance.

2. **[Minor / Responsive Scope] Margin Gutter Viewport Breakpoint**:
   - `MarginGutter.svelte` employs `@media (max-width: 1280px) { display: none; }`.
   - The test fixture properly configures `viewport={"width": 1440, "height": 900}` to exercise desktop cards. On smaller screens (<1280px), users access annotations via the Inspector Drawer Review tab.

3. **No Caveats Regarding Test Suite Pass Rate or Integrity**:
   - 100% test pass rate across all 8 E2E scenarios and 199 total project tests.

---

## 4. Conclusion

Milestone M3 (Headless Browser E2E Test Suite - R1) satisfies all requirements defined in `ORIGINAL_REQUEST.md` and `PROJECT.md`. The test suite is robust, fast (~26.5s), offline, reproducible, and provides complete test coverage of Features 18–24. The bug fixes in the Svelte viewer and bundler resolved real runtime issues without introducing regressions.

**Verdict**: **APPROVE**

---

## 5. Verification Method

To independently reproduce this verification:

1. **Run Playwright E2E Test Suite**:
   ```bash
   uv run pytest tests/e2e/ -v
   ```
   *Expected Result*: 8 passed in ~26 seconds with 0 errors.

2. **Run Full Test Suite (Zero Regression Guard)**:
   ```bash
   uv run pytest
   ```
   *Expected Result*: 199 passed in ~77 seconds with 0 failures.
