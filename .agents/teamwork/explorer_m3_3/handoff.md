# Technical Investigation Report: Annotation Persistence, Script Re-hydration, and Clean Bundle Export (Milestone M3 - R1)

**Agent**: Explorer M3.3 (`explorer_m3_3`)  
**Date**: 2026-10-11  
**Milestone**: M3 (Headless Browser E2E Test Suite - R1)  
**Authoritative References**: `.agents/teamwork/ORIGINAL_REQUEST.md`, `.agents/teamwork/PROJECT.md`, `.agents/teamwork/explorer_m3_3/DISPATCH.md`

---

## 1. Observation

Direct code observations from the interactive Svelte viewer (`viewer/src/`) and compilation bundler (`core/`):

### 1.1 Storage Persistence & Key Derivation
- **Key Derivation (`viewer/src/annotations/store.ts:22-26`)**:
  ```typescript
  function getDocumentKey(): string {
    const metaFingerprint = document.querySelector('meta[name="doc-fingerprint"]')?.getAttribute('content');
    const docTitle = document.querySelector('meta[name="doc-title"]')?.getAttribute('content') || document.title;
    return metaFingerprint || (docTitle ? `doc-${docTitle.toLowerCase().replace(/[^a-z0-9_-]+/g, '-')}` : 'md-style-doc');
  }
  ```
  - Storage key format: `storageKey = 'md-style:annotations:' + docKey;` (lines 30, 94).
  - Primary key: content-addressed SHA256 document fingerprint `<meta name="doc-fingerprint" content="...">`, injected by `AssetBundler` (`core/bundler.py:389, 553`).
  - Fallback key: slugified document title `<meta name="doc-title" content="...">` or `document.title` (`doc-${slug}`).
  - Ultimate fallback: `'md-style-doc'`.

- **Storage Schema & Serialization (`viewer/src/annotations/store.ts:92-113`)**:
  ```typescript
  function persist(items: DocumentAnnotation[], tombstones?: string[]) {
    const state = get({ subscribe });
    const storageKey = `md-style:annotations:${state.documentKey}`;
    try {
      let currentTombstones = tombstones || [];
      if (!tombstones) {
        const existing = localStorage.getItem(storageKey);
        if (existing) {
          const parsed = JSON.parse(existing);
          if (parsed && Array.isArray(parsed.tombstones)) {
            currentTombstones = parsed.tombstones;
          }
        }
      }
      localStorage.setItem(storageKey, JSON.stringify({
        annotations: items,
        tombstones: currentTombstones
      }));
    } catch (e) {
      console.warn('[Annotations] Failed to persist to localStorage:', e);
    }
    if (state.educativeMode) {
      highlighter.applyHighlights(items);
    }
  }
  ```
  - Schema in `localStorage`:
    ```json
    {
      "annotations": [
        {
          "id": "ann-...",
          "createdAt": "2026-10-11T12:00:00.000Z",
          "updatedAt": "2026-10-11T12:05:00.000Z",
          "author": "Reviewer",
          "category": "feedback",
          "text": "Comment markdown content",
          "range": {
            "blockIndex": 0,
            "quote": "Selected text quote",
            "prefixContext": "Preceding text...",
            "suffixContext": "Following text...",
            "textOffsetInBlock": 12
          },
          "resolved": false,
          "tags": []
        }
      ],
      "tombstones": [
        "ann-deleted-id-1",
        "ann-deleted-id-2"
      ]
    }
    ```
  - Supported categories (`types.ts:1`): `'feedback'`, `'correction'`, `'insight'`, `'commendation'`, `'question'`.
  - ID format (`store.ts:127`): `ann-${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 6)}`.

- **Annotation Card Editing (`viewer/src/annotations/AnnotationCard.svelte:17-33, 59-65, 92-100`)**:
  - Edit trigger: `<button class="action-icon-btn" on:click|stopPropagation={() => (isEditing = !isEditing)} title="Edit note">✏️</button>`.
  - Edit state: when `isEditing === true`, switches from markdown view to `.card-edit-box`.
  - Textarea: `<textarea class="edit-textarea" bind:value={editText} rows="2"></textarea>`.
  - Save button: `<button class="btn-sm-save" on:click={handleSaveEdit}>Save</button>`.
  - Cancel button: `<button class="btn-sm-cancel" on:click={() => (isEditing = false)}>Cancel</button>`.
  - Save handler: dispatches `update` event `{ id: annotation.id, text: editText.trim(), category: editCategory }`.
  - Store update (`store.ts:148-164`):
    ```typescript
    function updateAnnotation(id: string, text: string, category?: AnnotationCategory) {
      update(s => {
        const next = s.annotations.map(a => {
          if (a.id === id) {
            return {
              ...a,
              text,
              category: category || a.category,
              updatedAt: new Date().toISOString()
            };
          }
          return a;
        });
        persist(next);
        return { ...s, annotations: next };
      });
    }
    ```

- **Tombstone Deletion Mechanics (`viewer/src/annotations/store.ts:166-192`)**:
  - Delete trigger: `<button class="action-icon-btn delete-btn" on:click|stopPropagation={() => dispatch('delete', annotation.id)} title="Delete note">🗑️</button>`.
  - Store handler:
    ```typescript
    function deleteAnnotation(id: string) {
      update(s => {
        const next = s.annotations.filter(a => a.id !== id);
        const storageKey = `md-style:annotations:${s.documentKey}`;
        let currentTombstones: string[] = [];
        try {
          const existing = localStorage.getItem(storageKey);
          if (existing) {
            const parsed = JSON.parse(existing);
            if (parsed && Array.isArray(parsed.tombstones)) {
              currentTombstones = parsed.tombstones;
            }
          }
        } catch (e) {}

        if (!currentTombstones.includes(id)) {
          currentTombstones.push(id);
        }

        persist(next, currentTombstones);
        return {
          ...s,
          annotations: next,
          activeAnnotationId: s.activeAnnotationId === id ? null : s.activeAnnotationId
        };
      });
    }
    ```
  - Crucial Discovery: Deletion does **not** mutate objects to `{ _deleted: true }`. Instead, it purges the object from the `annotations` array and appends the ID to the separate `tombstones: string[]` array.

### 1.2 Embedded Script Tag Re-hydration
- **Embedded Script Tag Specification (`core/bundler.py:488-502`)**:
  - Element: `<script id="md-style-annotations" type="application/json">` placed before `</body>`.
  - Format:
    ```json
    {
      "version": "1.0",
      "document_fingerprint": "<hex>",
      "annotations": [ ... ]
    }
    ```
  - Backend bundling: `AssetBundler.assemble()` accepts `annotations: Optional[List[Dict[str, Any]]]` or extracts `frontmatter.get("annotations")`. It escapes `<` as `\u003c` via `json.dumps(...).replace("<", "\\u003c")` to prevent script breakout.

- **Re-hydration & Merging on Load (`viewer/src/annotations/store.ts:28-90`)**:
  ```typescript
  function init() {
    const docKey = getDocumentKey();
    const storageKey = `md-style:annotations:${docKey}`;

    // 1. Load baseline from embedded <script id="md-style-annotations">
    let embedded: DocumentAnnotation[] = [];
    const scriptEl = document.getElementById('md-style-annotations');
    if (scriptEl && scriptEl.textContent) {
      try {
        const parsed: AnnotationsManifest = JSON.parse(scriptEl.textContent);
        if (parsed && Array.isArray(parsed.annotations)) {
          embedded = parsed.annotations;
        }
      } catch (e) {
        console.warn('[Annotations] Failed to parse embedded #md-style-annotations:', e);
      }
    }

    // 2. Merge with localStorage session additions and tombstones
    let localSaved: DocumentAnnotation[] = [];
    let tombstones: string[] = [];
    try {
      const stored = localStorage.getItem(storageKey);
      if (stored) {
        const parsed = JSON.parse(stored);
        if (Array.isArray(parsed)) {
          localSaved = parsed;
        } else if (parsed && Array.isArray(parsed.annotations)) {
          localSaved = parsed.annotations;
          tombstones = Array.isArray(parsed.tombstones) ? parsed.tombstones : [];
        }
      }
    } catch (e) {
      console.warn('[Annotations] Failed to read localStorage:', e);
    }

    // Union by ID (localStorage overrides or appends, ignoring tombstones)
    const map = new Map<string, DocumentAnnotation>();
    const tombstoneSet = new Set(tombstones);

    for (const ann of embedded) {
      if (!tombstoneSet.has(ann.id)) {
        map.set(ann.id, ann);
      }
    }
    for (const ann of localSaved) {
      if (!tombstoneSet.has(ann.id)) {
        map.set(ann.id, ann);
      }
    }

    const merged = Array.from(map.values());
    update(s => ({
      ...s,
      documentKey: docKey,
      annotations: merged
    }));

    requestAnimationFrame(() => {
      highlighter.applyHighlights(merged);
    });
  }
  ```

### 1.3 Clean Bundle Export (`exportUpdatedHtmlBundle`)
- **Definition Location**: `viewer/src/annotations/export-bundle.ts:7-65`.
- **UI Invocation**: `viewer/src/InspectorDrawer.svelte:500-505`:
  ```svelte
  <button
    class="export-btn export-html-btn"
    on:click={() => exportUpdatedHtmlBundle($annotationStore.annotations, document.title)}
    title="Download standalone HTML report with comments embedded"
  >
    📦 Export HTML Bundle
  </button>
  ```
- **Export Pipeline Mechanics**:
  1. **Detached Clone**: `const clone = document.documentElement.cloneNode(true) as HTMLElement;` clones the complete document in memory without affecting live user interaction.
  2. **Transient UI Root Removal**:
     - Strips `#md-style-viewer-root` (the Svelte 5 application DOM tree).
     - Strips `.table-toolbar-container` (transient table filter bars).
     - Strips `.annotation-popover` (the floating comment composer).
     - Strips `.margin-gutter` (the floating side comment cards).
  3. **Unwrap Highlight Marks**:
     `clone.querySelectorAll('mark.md-annotation-mark').forEach(mark => { mark.replaceWith(...Array.from(mark.childNodes)); });`
     Restores original inline text nodes if DOM fallback highlights were used.
  4. **Reset Body Classes**:
     `body.classList.remove('inspector-open', 'paged-view');`
     Removes temporary layout shifts caused by open drawers or preview modes.
  5. **Update or Inject `#md-style-annotations`**:
     - Finds or creates `<script id="md-style-annotations" type="application/json">`.
     - Injects latest `$annotationStore.annotations`. Note: deleted/tombstoned items are completely absent from `$annotationStore.annotations`, cleanly eliminating tombstone baggage from the exported file.
     - Sanitizes JSON: `.replace(/</g, '\\u003c')` prevents script breakout attacks (`</script>`).
  6. **Re-inject Clean Empty Mounting Root**:
     Ensures `<div id="md-style-viewer-root"></div>` exists on `clone` so that on next document opening, `main.ts` can mount cleanly without duplicate root errors.
  7. **Trigger Download**:
     Assembles `'<!DOCTYPE html>\n' + clone.outerHTML`, creates a `Blob` of type `'text/html;charset=utf-8'`, and triggers an invisible `<a>` element download with filename `${slug}-annotated.html`.

---

## 2. Logic Chain

1. **Storage Persistence & Tombstone Invariance**:
   - Observations show that document annotations are identified by `getDocumentKey()`, prioritizing `meta[name="doc-fingerprint"]`. Because this fingerprint is a SHA256 digest of the HTML fragment, identical document revisions share the same storage partition, while updated builds automatically isolate their working state.
   - When an annotation is created or edited, it is immediately persisted to `localStorage.setItem("md-style:annotations:" + docKey, ...)`.
   - When an annotation is deleted, simply removing it from the `annotations` list in `localStorage` would be insufficient because baseline annotations embedded in `<script id="md-style-annotations">` cannot be deleted from the static HTML file on disk. On reload, `init()` would read `#md-style-annotations` and re-create the deleted item.
   - Recording deleted IDs in `tombstones: string[]` creates an immutable suppression filter: `tombstoneSet.has(ann.id)` guarantees that deleted embedded annotations remain suppressed across reloads and browser restarts.

2. **Re-hydration Precedence**:
   - `init()` merges embedded baseline annotations and localStorage working copies using a `Map<string, DocumentAnnotation>`.
   - Iterating over `embedded` first, then `localSaved`, ensures:
     1. Unmodified embedded annotations are loaded.
     2. Locally edited annotations override embedded counterparts (same ID).
     3. Newly created local annotations are appended.
     4. Any item present in `tombstones` is omitted from both sources.
   - This provides deterministic, conflict-free offline synchronization without external servers.

3. **Clean Bundle Export & DOM Integrity**:
   - The export process creates a truly portable, self-contained deliverable.
   - Removing `#md-style-viewer-root`, `.table-toolbar-container`, `.annotation-popover`, and `.margin-gutter` ensures that no transient Svelte components or event listeners are frozen into static HTML.
   - Unwrapping `<mark class="md-annotation-mark">` restores the original DOM text layout.
   - Escaping `<` as `\u003c` prevents XSS vulnerabilities if user comments contain HTML/script markup.
   - Including a pristine `<div id="md-style-viewer-root"></div>` guarantees that when the exported file is subsequently opened in a browser, Svelte 5's `mount(App, { target: root })` mounts into a virgin container without hydration mismatch or duplicated DOM nodes.

4. **Playwright E2E Verification Strategy**:
   - To verify that exported bundles re-open with 0 console errors and full annotation visibility:
     1. Create or edit an annotation in a test session.
     2. Trigger bundle export via `page.expect_download()` and clicking `.export-html-btn`.
     3. Save the downloaded HTML bundle to a temporary path.
     4. Open the downloaded bundle in an isolated browser context (`browser.new_context()`) to simulate a colleague opening the file on a clean machine with empty `localStorage`.
     5. Listen for `console` error events and `pageerror` events: assert `len(console_errors) == 0`.
     6. Verify that `#viewer-hud-ribbon` mounts, the comment badge displays the expected count, and the annotation card renders in `.margin-gutter` or the Inspector Drawer's Review tab.

---

## 3. Caveats

1. **Margin Gutter Viewport Threshold**:
   - `MarginGutter.svelte:119-123` hides the gutter when viewport width $\le 1280$px (`@media (max-width: 1280px) { .margin-gutter { display: none !important; } }`).
   - Playwright test fixtures must configure a viewport width of at least 1280px (e.g. `{"width": 1440, "height": 900}` or `{"width": 1920, "height": 1080}`) to assert visibility of `.margin-gutter .annotation-card`. Otherwise, annotations must be inspected inside `aside.drawer-container .comments-list`.
2. **CSS Custom Highlight API vs DOM `<mark>` Fallback**:
   - In modern Chromium (version 105+), `window.Highlight` and `CSS.highlights` are natively supported.
   - `DocumentHighlighter` uses CSS Custom Highlight API (`CSS.highlights.set("md-ann-" + cat, ...)`), which highlights text without inserting `<mark>` tags into the DOM.
   - Tests should not assume `<mark.md-annotation-mark>` exists in live DOM on Chromium; instead, verify highlighting via `CSS.highlights` inspection and verify presence of `.annotation-card` elements in the UI.
3. **Headless Text Selection Trigger**:
   - Drag-and-drop mouse movements in headless mode can be sensitive to subpixel line-height differences.
   - Triggering text selection programmatically via `document.createRange()`, `window.getSelection().addRange(range)`, and `document.dispatchEvent(new Event('selectionchange'))` is 100% deterministic and reliable across all environments.
4. **Local Web Origin vs `file://` Storage**:
   - In standard Chromium, `localStorage` on `file://` URLs is partitioned per directory or can be restricted depending on security flags.
   - Serving test fixtures via a lightweight local Python `http.server` fixture or configuring `browser.new_context()` ensures standard origin semantics for `localStorage`.

---

## 4. Conclusion

1. **Storage persistence** uses key `md-style:annotations:${docKey}` storing `{ annotations: [...], tombstones: [...] }`. Card editing triggers `annotationStore.updateAnnotation()`, updating `text` and `updatedAt`, immediately persisting to `localStorage`.
2. **Tombstone deletion** records deleted IDs in `tombstones: string[]`. During re-hydration in `init()`, `tombstoneSet` filters out deleted annotations from both embedded `#md-style-annotations` script tags and localStorage, preventing resurrection.
3. **Clean bundle export** (`exportUpdatedHtmlBundle` in `viewer/src/annotations/export-bundle.ts`) creates a detached clone, strips transient UI roots (`#md-style-viewer-root`, `.table-toolbar-container`, `.annotation-popover`, `.margin-gutter`), unwraps `<mark>` tags, resets body classes, injects sanitized `#md-style-annotations` with `\u003c` escaping, and adds a pristine `<div id="md-style-viewer-root"></div>`.
4. Automated Playwright test cases can cleanly verify that exported bundles re-open with 0 console errors and full annotation visibility using the recipes detailed below.

---

## 5. Verification Method: Playwright Test Recipes

The following exact, copy-pasteable test recipes are designed for `tests/e2e/test_svelte_viewer.py`:

### Recipe 1: Annotation Card Editing & Persistence Across Reload
Verifies Feature 22: card editing, `localStorage` serialization, and persistence across `page.reload()`.

```python
import json
import re
from playwright.sync_api import Page, expect

def test_annotation_card_editing_and_storage_persistence(page: Page, report_server_url: str):
    """
    Verifies that creating an annotation, editing its content via the card UI,
    and reloading the page preserves the updated annotation in localStorage and DOM.
    """
    page.goto(report_server_url)
    page.wait_for_selector("#viewer-hud-ribbon")

    # 1. Select text in document to trigger annotation popover
    page.evaluate("""() => {
        const p = document.querySelector('.report-content p, main p');
        const range = document.createRange();
        range.selectNodeContents(p.firstChild || p);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new Event('selectionchange'));
    }""")

    popover = page.locator(".annotation-popover")
    expect(popover).to_be_visible()

    # 2. Select 'Comment' category and compose note
    popover.locator(".popover-action-bar button.popover-btn[title='Add Comment']").click()
    composer = popover.locator(".popover-composer")
    expect(composer).to_be_visible()

    composer.locator("textarea.composer-textarea").fill("Initial draft note")
    composer.locator("button.btn-save").click()
    expect(popover).to_be_hidden()

    # 3. Verify card appears in Margin Gutter (viewport >= 1280px)
    gutter_card = page.locator(".margin-gutter .annotation-card").first
    expect(gutter_card).to_be_visible()
    expect(gutter_card.locator(".card-text")).to_contain_text("Initial draft note")

    # 4. Edit annotation via card pencil button
    gutter_card.locator("button.action-icon-btn[title='Edit note']").click()
    edit_box = gutter_card.locator(".card-edit-box")
    expect(edit_box).to_be_visible()

    edit_textarea = edit_box.locator("textarea.edit-textarea")
    edit_textarea.fill("Updated reviewed finding: **critical**")
    edit_box.locator("button.btn-sm-save").click()

    # Assert edited text is reflected in card
    expect(gutter_card.locator(".card-text")).to_contain_text("Updated reviewed finding: critical")

    # 5. Verify localStorage format and schema
    storage_data = page.evaluate("""() => {
        const key = Object.keys(localStorage).find(k => k.startsWith('md-style:annotations:'));
        return key ? JSON.parse(localStorage.getItem(key)) : null;
    }""")
    assert storage_data is not None, "localStorage annotation entry not found"
    assert "annotations" in storage_data
    assert "tombstones" in storage_data
    assert len(storage_data["annotations"]) == 1
    assert "critical" in storage_data["annotations"][0]["text"]

    # 6. Reload page and assert persistence
    page.reload()
    page.wait_for_selector("#viewer-hud-ribbon")

    reloaded_card = page.locator(".margin-gutter .annotation-card").first
    expect(reloaded_card).to_be_visible()
    expect(reloaded_card.locator(".card-text")).to_contain_text("Updated reviewed finding: critical")
```

---

### Recipe 2: Tombstone Deletion Mechanics
Verifies Feature 22: deleting an annotation appends its ID to `tombstones: string[]` in `localStorage` and prevents resurrection across `page.reload()`.

```python
def test_annotation_tombstone_deletion(page: Page, report_server_url: str):
    """
    Verifies that deleting an annotation removes it from the annotations array,
    appends its ID to the tombstones array in localStorage, and keeps it suppressed across reload.
    """
    page.goto(report_server_url)
    page.wait_for_selector("#viewer-hud-ribbon")

    # 1. Create an annotation
    page.evaluate("""() => {
        const p = document.querySelector('.report-content p, main p');
        const range = document.createRange();
        range.selectNodeContents(p.firstChild || p);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new Event('selectionchange'));
    }""")

    popover = page.locator(".annotation-popover")
    popover.locator(".popover-action-bar button.popover-btn[title='Add Insight']").click()
    popover.locator(".popover-composer textarea.composer-textarea").fill("Temporary insight to delete")
    popover.locator(".popover-composer button.btn-save").click()

    card = page.locator(".margin-gutter .annotation-card").first
    expect(card).to_be_visible()

    # Get created annotation ID
    ann_id = page.evaluate("""() => {
        const key = Object.keys(localStorage).find(k => k.startsWith('md-style:annotations:'));
        const data = JSON.parse(localStorage.getItem(key));
        return data.annotations[0].id;
    }""")
    assert ann_id.startswith("ann-")

    # 2. Click Delete button on card
    card.locator("button.action-icon-btn.delete-btn[title='Delete note']").click()

    # Card must disappear from DOM
    expect(page.locator(".margin-gutter .annotation-card")).to_have_count(0)

    # 3. Assert localStorage state: annotations empty, tombstones contains ann_id
    storage_data = page.evaluate("""() => {
        const key = Object.keys(localStorage).find(k => k.startsWith('md-style:annotations:'));
        return JSON.parse(localStorage.getItem(key));
    }""")
    assert len(storage_data["annotations"]) == 0
    assert ann_id in storage_data["tombstones"]

    # 4. Reload page and assert annotation remains suppressed
    page.reload()
    page.wait_for_selector("#viewer-hud-ribbon")
    expect(page.locator(".margin-gutter .annotation-card")).to_have_count(0)
```

---

### Recipe 3: Embedded Script Tag Re-hydration & Tombstone Overrides
Verifies Feature 23: documents with embedded `<script id="md-style-annotations">` re-hydrate on cold start, and local tombstones override embedded baseline annotations.

```python
from pathlib import Path
from core.bundler import AssetBundler
from core.themes import ThemeManager

def test_script_tag_rehydration_and_tombstone_override(page: Page, browser, tmp_path: Path):
    """
    Verifies that a document with pre-baked <script id="md-style-annotations">
    re-hydrates annotations into the store and gutter on cold load, and that
    deleting an embedded annotation records a tombstone that survives reload.
    """
    # 1. Compile test HTML document with 2 pre-baked annotations
    theme = ThemeManager().resolve_theme("forensic/cyber")
    bundler = AssetBundler(tmp_path / "test.md", allow_online=False)

    embedded_annotations = [
        {
            "id": "ann-baseline-keep",
            "createdAt": "2026-10-11T10:00:00.000Z",
            "author": "Auditor",
            "category": "insight",
            "text": "Baseline architectural observation",
            "range": {
                "blockIndex": 0,
                "quote": "System Architecture Overview",
                "prefixContext": "",
                "suffixContext": "",
                "textOffsetInBlock": 0
            },
            "resolved": False
        },
        {
            "id": "ann-baseline-remove",
            "createdAt": "2026-10-11T10:05:00.000Z",
            "author": "Auditor",
            "category": "correction",
            "text": "Baseline finding to be deleted",
            "range": {
                "blockIndex": 1,
                "quote": "Executive Summary",
                "prefixContext": "",
                "suffixContext": "",
                "textOffsetInBlock": 0
            },
            "resolved": False
        }
    ]

    html_content = bundler.assemble(
        html_fragment="<h1>System Architecture Overview</h1><p>Executive Summary content here.</p>",
        theme=theme,
        title="Rehydration Test Report",
        annotations=embedded_annotations
    )

    test_file = tmp_path / "rehydration-test.html"
    test_file.write_text(html_content, encoding="utf-8")

    # 2. Open in fresh context (clean localStorage)
    context = browser.new_context(viewport={"width": 1440, "height": 900})
    page = context.new_page()
    page.goto(f"file://{test_file.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    # Assert both pre-baked annotations re-hydrated from script tag
    gutter_cards = page.locator(".margin-gutter .annotation-card")
    expect(gutter_cards).to_have_count(2)

    # 3. Delete 'ann-baseline-remove'
    target_card = page.locator(".margin-gutter .annotation-card:has-text('Baseline finding to be deleted')")
    target_card.locator("button.action-icon-btn.delete-btn[title='Delete note']").click()

    # Only 1 card remains visible
    expect(gutter_cards).to_have_count(1)
    expect(gutter_cards.first).to_contain_text("Baseline architectural observation")

    # Verify tombstone stored in localStorage
    storage_data = page.evaluate("""() => {
        const key = Object.keys(localStorage).find(k => k.startsWith('md-style:annotations:'));
        return JSON.parse(localStorage.getItem(key));
    }""")
    assert "ann-baseline-remove" in storage_data["tombstones"]

    # 4. Reload page
    page.reload()
    page.wait_for_selector("#viewer-hud-ribbon")

    # Crucial assertion: despite static HTML containing both annotations in #md-style-annotations,
    # the tombstone in localStorage overrides and suppresses the deleted annotation.
    expect(page.locator(".margin-gutter .annotation-card")).to_have_count(1)
    expect(page.locator(".margin-gutter .annotation-card").first).to_contain_text("Baseline architectural observation")
    context.close()
```

---

### Recipe 4: Clean Bundle Export & Re-hydration with Zero Console Errors
Verifies Feature 24: `exportUpdatedHtmlBundle` unwraps marks, strips transient UI roots, and the exported bundle re-opens in a clean Playwright context with 0 console errors and full annotation visibility.

```python
def test_clean_bundle_export_and_rehydration_with_zero_console_errors(page: Page, browser, tmp_path: Path, report_server_url: str):
    """
    Verifies that clicking 'Export HTML Bundle' downloads an updated HTML file that:
    1. Does not contain transient UI roots or duplicate mount nodes.
    2. Has updated annotations embedded in #md-style-annotations with escaped < characters.
    3. Re-opens in an isolated browser context with ZERO console errors or page errors.
    4. Automatically re-hydrates all annotations into the Svelte viewer.
    """
    page.goto(report_server_url)
    page.wait_for_selector("#viewer-hud-ribbon")

    # 1. Add an annotation to the live document
    page.evaluate("""() => {
        const p = document.querySelector('.report-content p, main p');
        const range = document.createRange();
        range.selectNodeContents(p.firstChild || p);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new Event('selectionchange'));
    }""")

    popover = page.locator(".annotation-popover")
    popover.locator(".popover-action-bar button.popover-btn[title='Add Praise']").click()
    popover.locator(".popover-composer textarea.composer-textarea").fill("Bundle export test comment: **verified** <script>alert(1)</script>")
    popover.locator(".popover-composer button.btn-save").click()
    expect(popover).to_be_hidden()

    # 2. Open Inspector Drawer from HUD ribbon
    hud_btn = page.locator("#viewer-hud-ribbon button.action-btn:has-text('Inspector'), #viewer-hud-ribbon button.action-btn:has-text('Entities')").first
    hud_btn.click()
    drawer = page.locator("aside.drawer-container")
    expect(drawer).to_be_visible()

    # 3. Switch to Review tab
    review_tab = drawer.locator(".header-tab-bar button.header-tab-btn:has-text('Review')")
    review_tab.click()

    export_btn = drawer.locator("button.export-html-btn")
    expect(export_btn).to_be_visible()

    # 4. Trigger download of updated bundle
    with page.expect_download() as download_info:
        export_btn.click()
    download = download_info.value

    exported_file = tmp_path / download.suggested_filename
    download.save_as(exported_file)
    assert exported_file.is_file() and exported_file.stat().st_size > 0

    # 5. Static assertions on raw exported HTML content
    raw_html = exported_file.read_text(encoding="utf-8")

    # Transient UI containers must be absent
    assert "table-toolbar-container" not in raw_html, "Found transient table toolbar in exported bundle"
    assert "annotation-popover" not in raw_html, "Found transient annotation popover in exported bundle"
    assert "margin-gutter" not in raw_html, "Found transient margin gutter in exported bundle"
    assert "md-annotation-mark" not in raw_html, "Found un-unwrapped mark tags in exported bundle"

    # Mounting container must be clean and present
    assert '<div id="md-style-viewer-root"></div>' in raw_html, "Missing clean viewer root in exported bundle"

    # Embedded script tag must be present with escaped <
    assert '<script id="md-style-annotations" type="application/json">' in raw_html
    assert "\\u003cscript\\u003ealert(1)" in raw_html, "Script breakout character < was not sanitized to \\u003c"

    # 6. Re-open exported HTML in a fresh, isolated browser context (empty localStorage)
    clean_context = browser.new_context(viewport={"width": 1440, "height": 900})
    clean_page = clean_context.new_page()

    console_errors = []
    page_errors = []
    clean_page.on("console", lambda msg: console_errors.append(msg.text) if msg.type == "error" else None)
    clean_page.on("pageerror", lambda err: page_errors.append(str(err)))

    clean_page.goto(f"file://{exported_file.resolve()}")
    clean_page.wait_for_selector("#viewer-hud-ribbon")

    # Assert 0 console errors and 0 uncaught exceptions
    assert console_errors == [], f"Unexpected console errors upon re-hydration: {console_errors}"
    assert page_errors == [], f"Unexpected page errors upon re-hydration: {page_errors}"

    # Assert full annotation visibility
    gutter_card = clean_page.locator(".margin-gutter .annotation-card").first
    expect(gutter_card).to_be_visible()
    expect(gutter_card.locator(".card-text")).to_contain_text("Bundle export test comment: verified")

    clean_context.close()
```
