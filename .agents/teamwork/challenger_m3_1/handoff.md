# Handoff Report: Adversarial Verification & Stress Testing (Milestone M3 - R1)

**Agent**: `challenger_m3_1`  
**Role**: `teamwork_preview_challenger` (`critic`, `specialist`)  
**Date**: 2026-10-11T17:35:00Z  
**Milestone**: M3 (Headless Browser E2E Test Suite - R1)  
**Parent Orchestrator**: `2a97336d-5074-4aef-a112-3c18a332ea47`  
**Verdict**: **REQUEST_CHANGES**

---

## 1. Observation

### 1.1 Baseline E2E Suite Execution
The 8 baseline tests implemented by `worker_m3` in `tests/e2e/test_svelte_viewer.py` were executed directly:
```bash
uv run pytest tests/e2e/test_svelte_viewer.py -v
```
**Output**:
```text
tests/e2e/test_svelte_viewer.py::test_table_toolbar_filtering_and_search[chromium] PASSED [ 12%]
tests/e2e/test_svelte_viewer.py::test_inspector_drawer_catalog_and_filtering[chromium] PASSED [ 25%]
tests/e2e/test_svelte_viewer.py::test_inspectable_pill_selection_disambiguation[chromium] PASSED [ 37%]
tests/e2e/test_svelte_viewer.py::test_annotation_lifecycle_and_markdown_preview[chromium] PASSED [ 50%]
tests/e2e/test_svelte_viewer.py::test_storage_persistence_and_card_editing[chromium] PASSED [ 62%]
tests/e2e/test_svelte_viewer.py::test_tombstone_deletion_persistence[chromium] PASSED [ 75%]
tests/e2e/test_svelte_viewer.py::test_script_tag_rehydration_and_tombstone_override[chromium] PASSED [ 87%]
tests/e2e/test_svelte_viewer.py::test_clean_bundle_export_and_rehydration[chromium] PASSED [100%]
============================== 8 passed in 26.68s ==============================
```

### 1.2 Implementation of Adversarial Test Suite
To challenge the runtime under stress conditions, an adversarial test harness was built in `tests/e2e/test_adversarial_e2e.py` covering:
1. Multi-annotation lifecycle across reloads (`test_adversarial_multi_annotation_lifecycle`)
2. Corrupted JSON resilience in `localStorage` (`test_adversarial_corrupted_local_storage`)
3. Margin gutter card overlap in edit mode (`test_adversarial_margin_gutter_edit_overlap`)
4. Rapid tab switching and view thrashing in `InspectorDrawer` (`test_adversarial_rapid_inspector_tab_switching`)
5. Physical mouse drag-selection vs clean click disambiguation (`test_adversarial_physical_mouse_drag_selection`)
6. Adversarial XSS payload bundle export and rehydration (`test_adversarial_bundle_export_adversarial_payloads`)

### 1.3 Identification of Bug BUG-M3-01: Corrupted localStorage Blocks Persistence
In `viewer/src/annotations/store.ts` (lines 98–110):
```ts
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
```
When `localStorage` contains corrupted non-JSON data (e.g. `{broken_json_syntax: true, [unclosed`), `JSON.parse(existing)` throws an unhandled `SyntaxError`. This is caught by the outer `catch (e) { console.warn(...) }` block, causing `localStorage.setItem` to be completely skipped. As a result:
- Newly created annotations fail to persist to `localStorage`.
- The corrupted key is never repaired.
- Upon page reload, the user's newly created annotations are lost.

**Empirical Failure Output (`test_adversarial_corrupted_local_storage`)**:
```text
E           Failed: localStorage remained corrupted after addAnnotation: {broken_json_syntax: true, [unclosed
```

### 1.4 Identification of Bug BUG-M3-02: Margin Gutter Card Collision Overlaps Save Button
In `viewer/src/annotations/MarginGutter.svelte` (lines 20–59):
- Vertical stacking is calculated using a static height estimate `estimateCardHeight(item.annotation)` based only on the annotation text string (base height 90px).
- `calculatePositions()` only triggers when the `annotations` array changes, not when an individual card enters or exits edit mode (`isEditing = true`).
- When an upper card (e.g. Card 1) enters edit mode, its DOM renders `<div class="card-edit-box">` with a `<textarea>` and action buttons, expanding its DOM height to ~170px–200px.
- Because `MarginGutter` does not adjust positions, Card 2 below it remains at `top: 98px`, overlapping Card 1.
- When attempting to click Card 1's "Save" button, pointer events are physically intercepted by Card 2.

**Verbatim Playwright Failure Log (`test_adversarial_margin_gutter_edit_overlap`)**:
```text
E           playwright._impl._errors.TimeoutError: Locator.click: Timeout 3000ms exceeded.
E           Call log:
E             - waiting for locator(".margin-gutter .annotation-card").first.locator(".card-edit-box").locator("button.btn-sm-save")
E             - locator resolved to <button class="btn-sm-save svelte-38tb2b">Save</button>
E             - attempting click action
E               - element is visible, enabled and stable
E               - scrolling into view if needed
E               - done scrolling
E               - <div class="card-quote svelte-38tb2b">"Card 2: Directly adjacent note"</div> from <div class="gutter-item svelte-1guczdp">…</div> subtree intercepts pointer events
```

### 1.5 Full Suite Regression & XFail Verification
Running `uv run pytest tests/e2e/ -v`:
```text
tests/e2e/test_adversarial_e2e.py::test_adversarial_multi_annotation_lifecycle[chromium] PASSED [  7%]
tests/e2e/test_adversarial_e2e.py::test_adversarial_corrupted_local_storage[chromium] XFAIL [ 14%]
tests/e2e/test_adversarial_e2e.py::test_adversarial_margin_gutter_edit_overlap[chromium] XFAIL [ 21%]
tests/e2e/test_adversarial_e2e.py::test_adversarial_rapid_inspector_tab_switching[chromium] PASSED [ 28%]
tests/e2e/test_adversarial_e2e.py::test_adversarial_physical_mouse_drag_selection[chromium] PASSED [ 35%]
tests/e2e/test_adversarial_e2e.py::test_adversarial_bundle_export_adversarial_payloads[chromium] PASSED [ 42%]
tests/e2e/test_svelte_viewer.py::test_table_toolbar_filtering_and_search[chromium] PASSED [ 50%]
tests/e2e/test_svelte_viewer.py::test_inspector_drawer_catalog_and_filtering[chromium] PASSED [ 57%]
tests/e2e/test_svelte_viewer.py::test_inspectable_pill_selection_disambiguation[chromium] PASSED [ 64%]
tests/e2e/test_svelte_viewer.py::test_annotation_lifecycle_and_markdown_preview[chromium] PASSED [ 71%]
tests/e2e/test_svelte_viewer.py::test_storage_persistence_and_card_editing[chromium] PASSED [ 78%]
tests/e2e/test_svelte_viewer.py::test_tombstone_deletion_persistence[chromium] PASSED [ 85%]
tests/e2e/test_svelte_viewer.py::test_script_tag_rehydration_and_tombstone_override[chromium] PASSED [ 92%]
tests/e2e/test_svelte_viewer.py::test_clean_bundle_export_and_rehydration[chromium] PASSED [100%]

======================== 12 passed, 2 xfailed in 53.49s ========================
```
Full repository test execution (`uv run pytest`):
```text
================== 203 passed, 2 xfailed in 102.37s (0:01:42) ==================
```

---

## 2. Logic Chain

1. **Robust Areas Confirmed**:
   - *Physical Mouse Drag Disambiguation*: In `test_adversarial_physical_mouse_drag_selection`, physical mouse drag across an `.inspectable` pill verified that `window.getSelection().toString().trim().length > 0` successfully suppresses the Inspector Drawer and displays `.annotation-popover`. Conversely, a clean click without selection cleanly opens the drawer.
   - *Rapid State Transitions*: In `test_adversarial_rapid_inspector_tab_switching`, 15 rapid tab alternations between Entities and Review tabs, 5 entity drill-down/back cycles, and repeated drawer toggling completed with zero console errors and zero DOM desynchronizations.
   - *Adversarial Payload Sanitization*: In `test_adversarial_bundle_export_adversarial_payloads`, injecting `<script>alert(1)</script>` and `<img>` onerror payloads into an annotation demonstrated that exported bundles safely escape `<` to `\u003c` and DOMPurify prevents script execution in clean contexts.

2. **Defects Identified**:
   - *BUG-M3-01*: In `store.ts`, `persist()` attempts `const parsed = JSON.parse(existing)` to preserve tombstones without an inner `try/catch`. When `existing` is corrupted, the parse error aborts `localStorage.setItem(storageKey, ...)`, meaning the store cannot self-heal or persist any new notes until storage is externally wiped.
   - *BUG-M3-02*: In `MarginGutter.svelte`, `positionedCards` does not account for the expanded height of an active card edit box (`.card-edit-box`). When multiple annotations exist in the document and an upper card is edited, the lower card's `.gutter-item` overlaps the upper card's action buttons, physically blocking the user from clicking "Save" (verified by Playwright's pointer interception check).

---

## 3. Caveats

- Tests were run in headless Chromium with a 1440x900 viewport (per desktop gutter breakpoint requirement). Mobile viewport behavior (<1280px) hides margin cards by CSS design, so card overlap is specific to desktop gutter layout.
- The two discovered bugs do not crash the browser, but cause silent data loss (BUG-M3-01) and UI interaction failure (BUG-M3-02).

---

## 4. Conclusion

**Verdict: REQUEST_CHANGES**

Milestone M3 establishes an excellent foundation with 8 comprehensive E2E tests and robust Chromium fixtures. However, adversarial challenge revealed two concrete runtime defects that must be addressed:

1. **Fix BUG-M3-01 (`viewer/src/annotations/store.ts` and `core/assets/viewer.bundle.js`)**:
   Wrap `const parsed = JSON.parse(existing)` in an inner `try/catch` block inside `persist()`:
   ```ts
   if (!tombstones) {
     const existing = localStorage.getItem(storageKey);
     if (existing) {
       try {
         const parsed = JSON.parse(existing);
         if (parsed && Array.isArray(parsed.tombstones)) {
           currentTombstones = parsed.tombstones;
         }
       } catch {
         currentTombstones = [];
       }
     }
   }
   ```
2. **Fix BUG-M3-02 (`viewer/src/annotations/MarginGutter.svelte` and `core/assets/viewer.bundle.js`)**:
   Adjust `calculatePositions()` or dynamic card spacing so that when a card is in edit mode, subsequent cards shift down or add an extra vertical offset buffer (e.g. tracking `activeEditId` or using a dynamic layout / ResizeObserver) preventing adjacent cards from overlapping the Save button.
3. Once fixed, remove `@pytest.mark.xfail` from `tests/e2e/test_adversarial_e2e.py` so all 14 E2E tests pass cleanly.

---

## 5. Verification Method

1. **Verify Discovered Bugs (Current State)**:
   ```bash
   uv run pytest tests/e2e/test_adversarial_e2e.py -v
   ```
   *Expected Current Output*: 4 passed, 2 xfailed.
2. **Verify Post-Fix Resolution**:
   After applying the fixes to `store.ts`, `MarginGutter.svelte`, and rebuilding the viewer (`make build-viewer`):
   ```bash
   uv run pytest tests/e2e/ -v
   ```
   *Expected Post-Fix Output*: 14 passed in `tests/e2e/` with 0 xfailed and 0 failures.
3. **Full Regression Check**:
   ```bash
   uv run pytest
   ```
   *Expected Post-Fix Output*: 205 passed with 0 regressions across the entire test suite.
