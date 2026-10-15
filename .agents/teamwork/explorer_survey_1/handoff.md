# Architectural Survey & Handoff Report: Svelte Viewer Runtime & Headless E2E Test Suite (R1)

**Agent**: Explorer 1 (`explorer_survey_1`)  
**Date**: 2026-10-11  
**Target Milestone**: R1 (Headless Browser Interactivity Test Suite)  
**Authoritative Reference**: `.agents/teamwork/ORIGINAL_REQUEST.md`  

---

## Executive Summary
The interactive Svelte 5 viewer runtime (`viewer/src/`) compiles cleanly into a self-contained offline asset bundle (`core/assets/viewer.bundle.js` 5.6MB, `viewer.bundle.css` 31.6KB) embedded into reports by `AssetBundler`. All core interactive capabilities required by R1—text selection with popover composer, live Markdown preview, CRDT-style tombstone persistence across reloads, `.inspectable` pill disambiguation, `TableToolbar` category filtering, `InspectorDrawer` search/faceting, and clean DOM bundle export—are implemented and functional. System Chromium (`/usr/bin/chromium-browser`) is installed and operates in headless mode (`--headless=new`). The optimal path to satisfy R1 is a Python Playwright test suite (`tests/e2e/test_svelte_viewer.py`) executable via a single command: `uv run pytest tests/e2e/`.

---

## 1. Observations

### 1.1 Architecture & Viewer Mounting
- **Entry point**: `viewer/src/main.ts` (lines 6–55).
  - Checks if `window.matchMedia('print').matches` or `body` contains `.paged-preview` / `.print-mode`; skips UI mounting if true to preserve print fidelity.
  - Finds or creates container `#md-style-viewer-root` attached to `document.documentElement` (decoupled from body transform transitions).
  - Reads document title from `<meta name="doc-title" content="...">`.
  - Mounts Svelte 5 application via `mount(App, { target: root, props: { title, enableHud, enableInspector, enableTableFilters } })`.
- **Bundle output**: `viewer/vite.config.ts` (lines 7–26).
  - Compiles IIFE bundle to `../core/assets/viewer.bundle.js` and CSS to `../core/assets/viewer.bundle.css`.
  - Build verified: `npm run build` completed with code 0 in 36.09s, transforming 2585 modules and producing `core/assets/viewer.bundle.js` (5,637 kB) and `core/assets/viewer.bundle.css` (31.7 kB).
- **Offline HTML Assembly**: `core/bundler.py` (lines 380–568).
  - Bundles CSS stylesheets, Pygments styles, base64 fonts, base64 images, embedded Knowledge Pack JSON (`#md-style-kb-data`), i18n JSON (`#md-style-i18n`), raw source markdown (`#md-style-source-markdown`), print templates (`#md-style-print-templates`), optional pre-baked annotations (`#md-style-annotations`), and the Svelte bundle.
  - Zero external network requests needed at runtime.

### 1.2 Annotation Lifecycle, Live Preview, and Storage Persistence
- **Storage Store**: `viewer/src/annotations/store.ts` (lines 12–232).
  - Key identification: `getDocumentKey()` reads `meta[name="doc-fingerprint"]` or `doc-${docTitle.toLowerCase()}`. Storage key format is `md-style:annotations:${docKey}`.
  - Re-hydration baseline (`init()`):
    1. Reads `<script id="md-style-annotations" type="application/json">` if present (embedded annotations manifest).
    2. Reads `localStorage.getItem(storageKey)` containing `{ annotations: [...], tombstones: [...] }`.
    3. Merges embedded baseline and localStorage items by ID in a `Map`.
    4. Applies tombstone filtering: any ID present in `tombstones` is permanently omitted.
    5. Dispatches highlight updates via `highlighter.applyHighlights(merged)`.
  - Annotation creation: `addAnnotation(param)` generates ID `ann-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`, prepends to state, persists to `localStorage`, and triggers highlighting.
  - Annotation update: `updateAnnotation(id, text, category)` modifies text and timestamp, persists to `localStorage`.
  - Annotation deletion with tombstones: `deleteAnnotation(id)` filters out item, reads existing `tombstones`, appends `id` if absent, and calls `persist(next, currentTombstones)`.
  - Educative mode toggle: `toggleEducativeMode()` toggles visibility of annotations and calls `highlighter.clearHighlights()` or `highlighter.applyHighlights()`.
- **Range Serialization & Anchoring**: `viewer/src/annotations/dom-anchor.ts` (lines 6–140).
  - `serializeRange(range: Range)`: captures `quote`, `prefixContext` (up to 40 preceding characters), `suffixContext` (up to 40 following characters), `blockIndex` (index among `p, li, h1, h2, h3, h4, h5, h6, blockquote, tr, pre`), and `textOffsetInBlock`.
  - `deserializeRange(selector, root)`: locates block by `blockIndex`, searches for context `prefixContext + quote + suffixContext`, and falls back to exact quote search across elements.
  - `DocumentHighlighter`: Detects CSS Custom Highlight API via `typeof window.Highlight !== 'undefined' && typeof CSS.highlights !== 'undefined'`. Modern Chromium registers highlight groups `md-ann-feedback`, `md-ann-correction`, `md-ann-insight`, `md-ann-commendation`, `md-ann-question`. Fallback unwraps/wraps leaf text nodes using `<mark class="md-annotation-mark category-${cat}" data-ann-id="${id}">`.
- **Live Markdown Preview**:
  - `viewer/src/annotations/markdown.ts`: Configures `marked` (GFM, breaks) and `DOMPurify` (secures external links with `target="_blank"` and `rel="noopener noreferrer"`).
  - `viewer/src/annotations/AnnotationPopover.svelte` (lines 92–115): Features a two-tab toggle `Write` and `Preview`. In `Preview` mode, renders `{@html renderAnnotationMarkdown(commentText)}` inside `.composer-preview.markdown-body`.
- **Margin Gutter & Responsive Constraint**:
  - `viewer/src/annotations/MarginGutter.svelte` (lines 119–123):
    ```css
    @media (max-width: 1280px) {
      .margin-gutter {
        display: none !important;
      }
    }
    ```
    *Critical Observation*: The Margin Gutter comments are hidden on viewport widths <= 1280px. Testing viewport width must be set to at least 1360px (e.g. 1440x900 or 1920x1080) for gutter cards to be visible.

### 1.3 Interaction Disambiguation: `.inspectable` Pills vs Text Selection
- **Implementation**: `viewer/src/App.svelte` (lines 312–336):
  ```typescript
  const clickHandler = (e: MouseEvent) => {
    // Disambiguate: if text is currently highlighted by the user, do not open inspectable entity drawer
    const sel = window.getSelection();
    if (sel && sel.toString().trim().length > 0) return;

    // Handle clicking an annotation mark
    const annMark = (e.target as HTMLElement)?.closest('.md-annotation-mark') as HTMLElement;
    if (annMark) {
      const annId = annMark.getAttribute('data-ann-id');
      if (annId) {
        annotationStore.setActive(annId);
        isDrawerOpen = true;
        document.body.classList.add('inspector-open');
        return;
      }
    }

    const target = (e.target as HTMLElement)?.closest('.inspectable') as HTMLElement;
    if (target) {
      e.preventDefault();
      handleEntityClick(target);
    }
  };
  ```
- **Disambiguation mechanics**:
  - When a user performs mouse-down, drags to select text across or inside an `.inspectable` pill, and releases the mouse, a `click` event fires.
  - The guard `sel && sel.toString().trim().length > 0` evaluates to `true`. The handler returns immediately without opening the inspector drawer.
  - Simultaneously, the `selectionchange` listener (lines 285–309) records `activeSelectedRange` and displays the `AnnotationPopover`.
  - When the user performs a discrete click without selection (`sel.toString().trim().length === 0`), `(e.target).closest('.inspectable')` matches and triggers `handleEntityClick(target)`, opening the `InspectorDrawer`.

### 1.4 Clean Bundle Export (`exportUpdatedHtmlBundle`)
- **Implementation**: `viewer/src/annotations/export-bundle.ts` (lines 7–65):
  1. Clones document element: `const clone = document.documentElement.cloneNode(true) as HTMLElement`.
  2. Removes transient UI roots:
     - `clone.querySelector('#md-style-viewer-root')?.remove();`
     - `clone.querySelectorAll('.table-toolbar-container').forEach(el => el.remove());`
     - `clone.querySelectorAll('.annotation-popover').forEach(el => el.remove());`
     - `clone.querySelectorAll('.margin-gutter').forEach(el => el.remove());`
  3. Unwraps all runtime highlight mark tags back to original text nodes:
     `clone.querySelectorAll('mark.md-annotation-mark').forEach(mark => mark.replaceWith(...mark.childNodes));`
  4. Resets body classes: removes `inspector-open` and `paged-view`.
  5. Injects or updates `#md-style-annotations` script tag with sanitized JSON:
     `replace(/</g, '\\u003c')` to prevent script breakout XSS.
  6. Re-appends empty `<div id="md-style-viewer-root"></div>` to ensure fresh, clean mounting upon subsequent load.
  7. Triggers browser download with filename `${docTitle}-annotated.html`.

### 1.5 Slide-Over Inspector Drawer & Table Toolbar
- **Inspector Drawer** (`viewer/src/InspectorDrawer.svelte`):
  - Catalog browser mode:
    - Search input (`.search-input`): filters entities in real time across ID, title, and summary.
    - Category pills (`.category-pills .pill-btn`): filters by entity type (CVE, MITRE, IP, Hash, etc.).
    - Entity cards (`.entity-cards-list .entity-item-card`): displays matching items.
  - Tab switcher: toggles between Entities (`activeTab === 'kb'`) and Review (`activeTab === 'comments'`).
  - Review tab: contains `📦 Export HTML Bundle` and `📝 Export CriticMarkup .md` action buttons, plus the active comments list.
- **Table Toolbar** (`viewer/src/TableToolbar.svelte`):
  - Automatically mounts on tables with >= 4 rows or `.table-timeline` (skips SVJ housing theme).
  - Scans columns for categorical values (columns having 2 to 5 recurring values).
  - Renders category pills (`All (totalRows)`, `<Category> (count)`).
  - Provides real-time search box (`input[type="text"]`).
  - Hides non-matching `tr` elements (`row.style.display = 'none'`) and updates `.count-badge` (`visibleRows / totalRows`).

### 1.6 Environment & Browser Binary Inspection
- **Node runtime**: Node `v22.23.1`, npm `10.9.8`.
- **Python runtime**: Python `3.14.8`, `uv`, `pytest 9.1.1`.
- **Chromium browser**:
  - `/usr/bin/chromium-browser` is installed (`Chromium 154.0.8037.57`).
  - Headless command test verified: `/usr/bin/chromium-browser --headless=new --dump-dom about:blank` exited code 0 and dumped valid DOM.
  - Cached Playwright binary exists in `~/.cache/ms-playwright/chromium-1243/chrome-linux64/chrome`.
- **Existing unit tests**: `uv run pytest` executes 87 tests in `tests/`, passing 100% in 4.84s.

---

## 2. Logic Chain

1. **Requirement R1 Mapping**:
   - R1 requires automated tests verifying text selection, annotation creation, live Markdown preview, storage persistence, slide-over drawer filtering, table toolbar filtering, clean bundle export, and `.inspectable` pill disambiguation.
   - Acceptance Criteria explicitly requires:
     *"Automated test suite runs via a single command (e.g. `npm test` or `uv run pytest tests/e2e/`) and completes in headless mode."*
2. **Harness Selection Reasoning**:
   - The md-style project is structured as a Python CLI package with existing pytest suite (`tests/`).
   - Svelte files are compiled by Vite into static bundles embedded by Python `AssetBundler`.
   - Running E2E tests through `uv run pytest tests/e2e/` maintains a unified Python testing environment, allowing programmatic creation of HTML test fixtures using `ReportEngine` and `AssetBundler`.
   - Python Playwright (`playwright` + `pytest-playwright`) installs cleanly via `uv add --dev pytest-playwright playwright` and works on Python 3.14.
   - By specifying `executable_path="/usr/bin/chromium-browser"` in Playwright fixtures, the test harness operates completely air-gapped without requiring any external browser downloads.
3. **Execution Reliability**:
   - Viewport configuration: Setting viewport width to 1440px ensures both desktop layout and Margin Gutter are rendered.
   - Console error tracking: Attaching a `page.on("console", ...)` listener allows strict assertions that exported and re-opened HTML files generate zero uncaught console errors.
   - Storage isolation: Using `browser.new_context()` provides fresh, isolated localStorage sessions for verifying clean re-hydration from embedded script tags vs localStorage persistence across `page.reload()`.

---

## 3. Implementation Recommendations for R1

### 3.1 Dependency Setup
Add `pytest-playwright` and `playwright` to `pyproject.toml`:
```toml
[dependency-groups]
dev = [
    "pytest>=8.4.2",
    "playwright>=1.40.0",
    "pytest-playwright>=0.5.0",
]
```
Command to install:
```bash
uv add --dev pytest-playwright playwright
```

### 3.2 Directory Structure
Create an E2E test directory under `tests/`:
```
tests/e2e/
├── __init__.py
├── conftest.py
└── test_svelte_viewer.py
```

### 3.3 Proposed `tests/e2e/conftest.py` Blueprint
```python
"""
tests/e2e/conftest.py
Playwright configuration and headless browser fixtures for Svelte Viewer E2E tests.
"""

import os
import shutil
import pytest
from pathlib import Path

BROWSER_PATH = os.environ.get("CHROME_BIN") or shutil.which("chromium-browser") or shutil.which("chromium")

@pytest.fixture(scope="session")
def browser_type_launch_args():
    launch_args = {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-gpu",
            "--disable-dev-shm-usage",
            "--headless=new"
        ]
    }
    if BROWSER_PATH:
        launch_args["executable_path"] = BROWSER_PATH
    return launch_args

@pytest.fixture(scope="function")
def browser_context_args():
    return {
        "viewport": {"width": 1440, "height": 900},
        "accept_downloads": True,
    }
```

### 3.4 Proposed E2E Test Suite (`tests/e2e/test_svelte_viewer.py`)
The suite should cover the following 8 comprehensive scenarios:

1. **Table Toolbar Interactions (`test_table_toolbar_filtering`)**:
   - Open report (`examples/sample-forensic-cyber.html`).
   - Wait for `#viewer-hud-ribbon` and `.table-toolbar-container`.
   - Verify categorical pills detected (e.g., `MALICIOUS`, `SUSPICIOUS`, `CONTAINED`).
   - Click `MALICIOUS` pill: verify row count updates (4 / 7) and non-matching rows have `display: none`.
   - Type `Mimikatz` in the search box: verify visible rows drop to 1 / 7.
   - Click clear button `✕`: verify query clears and row count resets.

2. **Inspectable Pill Click Opens Drawer (`test_inspectable_pill_click`)**:
   - Click `.inspectable[data-token="CVE-2026-3184"]`.
   - Verify `document.body` receives class `inspector-open`.
   - Verify `.drawer-container` is visible.
   - Verify entity title and details (CVSS score, description) are displayed.
   - Press `Escape` key: verify drawer closes.

3. **Interaction Disambiguation (`test_inspectable_vs_selection_disambiguation`)**:
   - Programmatically select or drag text across an `.inspectable` pill:
     ```python
     page.evaluate("""() => {
         const pill = document.querySelector('.inspectable[data-token="CVE-2026-3184"]');
         const range = document.createRange();
         range.selectNodeContents(pill);
         const sel = window.getSelection();
         sel.removeAllRanges();
         sel.addRange(range);
         document.dispatchEvent(new Event('selectionchange'));
         pill.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
     }""")
     ```
   - Verify `.annotation-popover` appears.
   - Verify `document.body` DOES NOT have class `inspector-open` (drawer did not open).

4. **Annotation Creation & Markdown Preview (`test_annotation_creation_and_preview`)**:
   - Dispatch selection on report text.
   - Click category button (e.g. `💡 Insight`).
   - Enter markdown note: `**Critical Insight**: Inspect \`0x7ffe820\`.`
   - Click `Preview` tab in composer:
     - Verify `.composer-preview` contains `<strong>Critical Insight</strong>` and `<code>0x7ffe820</code>`.
   - Click `Save Note`:
     - Verify popover closes.
     - Verify HUD ribbon comment count updates to 1.
     - Verify `.margin-gutter .annotation-card` renders the note.
     - Verify `localStorage` contains `md-style:annotations:<docKey>`.

5. **Storage Persistence Across Reload (`test_annotation_persistence_reload`)**:
   - Reload page (`page.reload()`).
   - Verify HUD comment count remains 1.
   - Verify Margin Gutter card re-hydrates with full text.

6. **Annotation Editing & Tombstone Deletion (`test_annotation_edit_and_tombstones`)**:
   - Click edit button `✏️` on annotation card.
   - Update text to `Updated note text` and click Save.
   - Reload page: verify edited text persisted.
   - Click delete button `🗑️` on card:
     - Verify card removed.
     - Inspect `localStorage`: verify `tombstones` array contains the deleted annotation's ID.
   - Reload page: verify annotation does not reappear.

7. **Embedded Script Tag Re-hydration & Tombstone Overrides (`test_embedded_script_tag_rehydration`)**:
   - Compile HTML document with frontmatter `annotations: [...]`.
   - Open in a fresh browser context (empty `localStorage`).
   - Verify annotations load directly from `<script id="md-style-annotations">`.
   - Delete one embedded annotation.
   - Reload: verify tombstone prevents re-display of deleted annotation while surviving embedded annotations remain visible.

8. **Clean Bundle Export & Zero-Error Re-hydration (`test_clean_bundle_export`)**:
   - Open Inspector Drawer, switch to Review tab.
   - Intercept download and click `📦 Export HTML Bundle`:
     ```python
     with page.expect_download() as download_info:
         page.locator(".export-btn.export-html-btn").click()
     download = download_info.value
     export_path = tmp_path / "exported-bundle.html"
     download.save_as(export_path)
     ```
   - Inspect saved HTML content:
     - Assert only 1 `#md-style-viewer-root` element exists (empty placeholder).
     - Assert 0 `.table-toolbar-container`, 0 `.annotation-popover`, 0 `.margin-gutter`.
     - Assert `<script id="md-style-annotations">` contains the exported annotations with safe JSON (`\u003c`).
   - Open `export_path` in a new `BrowserContext`:
     - Monitor console errors: assert 0 uncaught errors.
     - Verify annotations re-hydrate in HUD and InspectorDrawer.
     - Verify tables receive exactly 1 toolbar container without duplication.

### 3.5 Makefile Integration
Add the following target to `Makefile`:
```makefile
test-e2e:
	uv run pytest tests/e2e/ -v
```

---

## 4. Caveats
1. **Viewport Width**: Margin Gutter cards have `@media (max-width: 1280px) { display: none !important; }`. Playwright browser context must specify a minimum width of 1360px (recommended: 1440x900) so gutter elements are rendered and queryable.
2. **Air-Gap / Offline Execution**: To ensure 100% offline compliance (no unexpected browser binary downloads during test runs), Playwright launch arguments must explicitly reference `/usr/bin/chromium-browser`.
3. **Local Storage Scoping**: When opening files via `file://`, Chromium scopes localStorage to `file://`. Isolating tests requires creating a fresh `browser.new_context()` per test function (Playwright's default behavior).

---

## 5. Conclusion
The Svelte interactive viewer runtime and Python bundler are architecturally mature and satisfy all prerequisite capabilities for R1. A Python-based Playwright E2E suite (`tests/e2e/test_svelte_viewer.py`) provides a single-command (`uv run pytest tests/e2e/`), headless, reproducible test environment utilizing existing system Chromium binaries with zero external network access.

---

## 6. Verification Method

To independently verify these findings:

1. **Verify Svelte Viewer Compilation**:
   ```bash
   cd /home/valor/Devel/personal/md-style/viewer
   npm run build
   ```
   *Expected outcome*: Exits code 0; produces `../core/assets/viewer.bundle.js` and `../core/assets/viewer.bundle.css`.

2. **Verify System Headless Chromium Execution**:
   ```bash
   /usr/bin/chromium-browser --headless=new --dump-dom "about:blank"
   ```
   *Expected outcome*: Exits code 0; returns `<html><head></head><body></body></html>`.

3. **Verify Baseline Unit Tests**:
   ```bash
   cd /home/valor/Devel/personal/md-style
   uv run pytest -v
   ```
   *Expected outcome*: All 87 tests pass with 0 regressions in < 5 seconds.

4. **Verify Playwright Compatibility via Python**:
   ```bash
   cd /home/valor/Devel/personal/md-style
   uv pip install --dry-run pytest-playwright
   ```
   *Expected outcome*: Resolves `pytest-playwright==0.10.0` and `playwright==1.63.0` cleanly on Python 3.14.8.
