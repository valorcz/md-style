# Technical Investigation Report: Svelte Viewer DOM Selectors & UI Interaction Flows (Milestone M3 - R1)

## 1. Observation

Direct code observations from `/home/valor/Devel/personal/md-style/viewer/src/` and `/home/valor/Devel/personal/md-style/core/`:

### A. Viewer Lifecycle & Root Mounting
- **File**: `viewer/src/main.ts:15-36`
  - Mount root: `#md-style-viewer-root` appended to `document.documentElement` (`document.documentElement.appendChild(root)`).
  - Print/Paged media suppression: if `window.matchMedia('print').matches` or `body.classList.contains('paged-preview')` or `body.classList.contains('print-mode')`, overlay mounting is suppressed (`enableHud = false`, `enableInspector = false`, `enableTableFilters = false`).
  - Svelte 5 mount: `mount(App, { target: root, props: { title, enableHud, enableInspector, enableTableFilters } })`.

### B. TableToolbar.svelte Mounting & Interactions
- **Mount Condition (`viewer/src/App.svelte:114-143`)**:
  - `setupTableToolbars()` iterates over all `table` elements.
  - Skip rule: if `document.body.className.includes('theme-svj')`, returns immediately.
  - Mount rule: `const rowCount = tbody ? tbody.querySelectorAll('tr').length : 0;` and `table.classList.contains('table-timeline')`.
  - Condition: `if (rowCount < 4 && !isTimeline) return;`.
  - Insertion: Container `<div class="table-toolbar-container">` is inserted before the `table` via `parent.insertBefore(container, table)`.
- **Categorical Column Auto-Discovery (`viewer/src/TableToolbar.svelte:28-49`)**:
  - Iterates over columns `col = 0 .. numCols-1`.
  - Computes counts of unique text cell values (trimmed, 1 to 30 characters).
  - Condition: `if (uniqueVals.length >= 2 && uniqueVals.length <= 5 && uniqueVals.length < rows.length) { categoryColumnIdx = col; categoryPills = uniqueVals.map(name => ({ name, count: counts[name] })); break; }`.
- **DOM Selectors & Elements (`viewer/src/TableToolbar.svelte:99-136`)**:
  - Container: `.table-toolbar-container`
  - Toolbar root: `.table-toolbar` (with `aria-label="Table filter controls"`)
  - Left section: `.table-toolbar .toolbar-left`
  - Right section: `.table-toolbar .toolbar-right`
  - Category Pills: `.table-toolbar .category-pills`
    - "All" Button: `.category-pills button.pill-btn` with text `All ({totalRows})`. Has class `.active` when `selectedCategory === 'ALL'`.
    - Specific Category Button: `.category-pills button.pill-btn` with text `{pill.name} ({pill.count})`. Has class `.active` when active.
  - Live Search Box: `.table-toolbar .search-box`
    - Search input: `.search-box input[type="text"]` (or `input[aria-label="Filter rows"]`). Placeholder `Filter table records...` (or localized). Fires `on:input={applyFilter}`.
    - Clear button: `.search-box button.clear-btn` (rendered only if `query` is non-empty, text `✕`, title `Clear filter`). Fires `on:click={clearQuery}`.
  - Count Badge: `.toolbar-right .count-badge`
    - Text: `{visibleRows} / {totalRows}`.
- **Row Hiding Mechanism (`viewer/src/TableToolbar.svelte:60-79`)**:
  - Sets `row.style.display = ''` on matching rows; `row.style.display = 'none'` on non-matching rows.
  - Print restoration (`viewer/src/TableToolbar.svelte:233-240`):
    `@media print { .table-toolbar { display: none !important; } :global(tr[style*="display: none"]) { display: table-row !important; } }`.

### C. InspectorDrawer.svelte Opening & Catalog / Detail States
- **Drawer Opening Triggers**:
  1. HUD Ribbon: `#viewer-hud-ribbon button.action-btn` (title `Inspect Knowledge Entities, Review Notes & Comments`). Click dispatches `toggleInspector` (`App.svelte:72-78`), toggles `body.inspector-open`, opens Drawer in catalog mode (`entity = null`).
  2. Inspectable Pill Click: `.inspectable` element (`App.svelte:329-334`). Click dispatches `handleEntityClick(target)`, sets `selectedEntity`, toggles `body.inspector-open`, opens Drawer in single entity detail view.
  3. Annotation Mark Click: `.md-annotation-mark` (`App.svelte:318-326`). Click sets `annotationStore.setActive(annId)`, opens Drawer.
- **Drawer Root Container (`viewer/src/InspectorDrawer.svelte:115-116`)**:
  - `<aside class="drawer-container" aria-label="Entity Details Inspector">`
  - Fixed slide-over: `position: fixed; top: 40px; right: 0; width: 440px; z-index: 9999;`.
  - Close button: `.drawer-header button.close-btn` (text `✕`).
  - Esc keydown: `handleKeydown(event)` calls `onClose()` when `event.key === 'Escape'`.
- **Mode 1: Catalog Browser View (`entity === null`) (`viewer/src/InspectorDrawer.svelte:132-148, 541-623`)**:
  - Header Tabs: `.drawer-header .header-tab-bar`
    - Entities Tab: `.header-tab-bar button.header-tab-btn:has-text("Entities")` (active when `activeTab === 'kb'`).
    - Review Tab: `.header-tab-bar button.header-tab-btn:has-text("Review")` (active when `activeTab === 'comments'`).
  - Search Input: `.drawer-body .search-box input.search-input` (placeholder `Search knowledge entities...`).
  - Clear Search Button: `.drawer-body .search-box button.search-clear-btn` (text `✕`).
  - Category Pills: `.drawer-body .category-pills button.pill-btn`
    - "All" pill: `All ({entityList.length})` (has `.active` class when `selectedCategory === 'all'`).
    - Type pill: `{CAT} ({count})` (e.g. `CVE (3)`, `WINEVENT (4)`).
  - Entity Cards: `.drawer-body .entity-cards-list .entity-item-card`
    - Child items: `.item-header .item-id`, `.item-header .badge`, `.item-title`, `.item-summary`.
    - Clicking `.entity-item-card` transitions to Single Entity Detail View (`entity = item`).
    - Empty results: `.drawer-body .entity-cards-list .no-results-msg`.
- **Mode 2: Single Entity Detail View (`entity !== null`) (`viewer/src/InspectorDrawer.svelte:119-130, 153-494`)**:
  - Header Back Button: `.drawer-header button.nav-back-btn` (text `← All Entities`). Clicking it resets `entity = null`, returning to Catalog Browser View.
  - Header Badges: `.drawer-header .header-badges .badge.badge-{severity}`.
  - Hero Card: `.entity-hero-card.type-{type}` with `h2.entity-title`, `.token-row code.entity-id`, `.token-row button.copy-btn`.
  - Type-specific blocks:
    - CVE: `.cvss-hero-gauge.cvss-{level}` with `.gauge-score` and `.gauge-vector`.
    - CWE: `.cwe-rank-badge .rank-position`.
    - Windows Event / Threat tips: `.tactical-box.tactical-tips` and `.tactical-box.tactical-threat`.
    - EVTX / Network IP: `.tactical-box.tactical-telemetry`.
    - Hash: `.tactical-box.tactical-threat .vt-ratio-badge`.
  - Sections:
    - Summary: `.drawer-section .summary-text`
    - Metrics: `.drawer-section .metrics-grid .metric-card`
    - Pivot links: `.drawer-section .relationship-chips button.rel-chip` (clicking pivots to target entity).
    - Attributes table: `.drawer-section table.attributes-table`
    - Details table: `.drawer-section table.details-table`
- **Mode 3: Review Tab (`activeTab === 'comments'`) (`viewer/src/InspectorDrawer.svelte:495-540`)**:
  - Export Row: `.comments-management-view .export-actions-row`
    - Export HTML button: `.export-actions-row button.export-html-btn` (text `📦 Export HTML Bundle`).
    - Export CriticMarkup button: `.export-actions-row button.export-md-btn` (text `📝 Export CriticMarkup .md`).
  - Comments List: `.comments-management-view .comments-list`
    - Contains `.annotation-card` items (`AnnotationCard.svelte`).
    - Empty notice: `.comments-management-view .empty-comments-notice`.

### D. Annotation Creation & Popover
- **Trigger (`viewer/src/App.svelte:285-308`)**:
  - Window selection event: `selectionchange`.
  - Validates `!sel.isCollapsed && sel.toString().trim()`.
  - Boundary check: `const root = document.querySelector('.report-content') || document.querySelector('main');` must contain selection ancestor.
  - Bounding box position: `selectionPopoverPos = { x: rect.left + rect.width / 2, y: rect.top }`.
- **Popover Element (`viewer/src/annotations/AnnotationPopover.svelte:55-123`)**:
  - Container: `.annotation-popover[role="dialog"][aria-label="Add annotation to selection"]`.
  - Position: `style="top: ...px; left: ...px;"` with transform `translate(-50%, -100%) translateY(-10px)`.
- **Initial Action Bar State (`!isComposing`)**:
  - Container: `.annotation-popover .popover-action-bar`
  - Category buttons: `.popover-action-bar button.popover-btn`:
    - Comment: `button.popover-btn[title="Add Comment"]` (icon `💬`, label `Comment`, color `#0284c7`)
    - Correction: `button.popover-btn[title="Add Correction"]` (icon `✏️`, label `Correction`, color `#f43f5e`)
    - Insight: `button.popover-btn[title="Add Insight"]` (icon `💡`, label `Insight`, color `#f59e0b`)
    - Praise: `button.popover-btn[title="Add Praise"]` (icon `🎓`, label `Praise`, color `#10b981`)
    - Question: `button.popover-btn[title="Add Question"]` (icon `❓`, label `Question`, color `#a855f7`)
  - Cancel button: `.popover-action-bar button.popover-close-btn` (text `✕`).
- **Composer State (`isComposing === true`)**:
  - Container: `.annotation-popover .popover-composer`
  - Header: `.composer-header`
    - Title: `.composer-title`
    - Author input: `.composer-author-box input.author-input` (placeholder `Your Name`, default `Reviewer`)
    - Mode tabs:
      - Write: `.composer-mode-bar button.mode-tab-btn:has-text("Write")` (has `.active` class when in write mode)
      - Preview: `.composer-mode-bar button.mode-tab-btn:has-text("Preview")` (has `.active` class when previewing; disabled when textarea is empty)
  - Quote snippet: `.popover-composer .composer-quote`
  - Textarea: `.popover-composer textarea.composer-textarea`
  - Live Preview Pane: `.popover-composer .composer-preview.markdown-body` (rendered when `showPreview === true`; runs through `marked` and `DOMPurify`)
  - Actions: `.popover-composer .composer-actions`
    - Back button: `button.btn-cancel` (text `Back`)
    - Save button: `button.btn-save` (text `Save Note`, disabled if textarea is whitespace only)
- **Save Action (`App.svelte:345-361`)**:
  - Dispatches `create` event, serializes DOM range with `serializeRange(range)`.
  - Calls `annotationStore.addAnnotation({ category, text, author, range })`.
  - Clears selection (`window.getSelection()?.removeAllRanges()`).
  - Persists to `localStorage` key `md-style:annotations:{docKey}`.
  - Highlights text in DOM (`mark.md-annotation-mark.category-{category}`).
  - Appears in Margin Gutter (`aside.margin-gutter .annotation-card`) if viewport width >= 1280px.
  - Increments HUD comment badge (`💬 1`).

### E. Interaction Disambiguation (`.inspectable` vs Text Selection)
- **Code Observation (`viewer/src/App.svelte:312-336`)**:
  ```ts
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

---

## 2. Logic Chain

1. **Table Filtering Behavior**:
   - `setupTableToolbars()` injects `.table-toolbar-container` containing `<TableToolbar>` directly before each eligible `table` (rows >= 4 or timeline).
   - In `TableToolbar.svelte`, `initTableStats()` scans columns for categorical data (2-5 unique values).
   - When a category pill is clicked (`selectCategory(cat)`), `applyFilter()` evaluates each row:
     - Category match: `cellVal.toLowerCase() === selectedCategory.toLowerCase()` (or `selectedCategory === 'ALL'`).
     - Query match: `rowText.includes(query.trim().toLowerCase())`.
     - Matching rows receive `row.style.display = ''`.
     - Non-matching rows receive `row.style.display = 'none'`.
     - Count badge updates to `${visibleRows} / ${totalRows}`.

2. **Inspector Drawer Opening & State Transitions**:
   - When HUD Inspector button is clicked, `isDrawerOpen` toggles, `document.body` gets `.inspector-open`, and `<aside class="drawer-container">` renders with `entity = null`.
   - In this state, the drawer shows two tabs: "Entities" and "Review".
   - In "Entities" tab, filtering by query or category pills updates `filteredEntities`, rendering cards with `.item-id` and `.item-title`.
   - Clicking an entity card sets `entity = item`, transitioning the drawer into Single Entity Detail View with `.entity-hero-card` and back button `.nav-back-btn`.
   - Clicking `.nav-back-btn` sets `entity = null`, returning to the catalog view.

3. **Disambiguation Mechanism**:
   - `.inspectable` elements are inline spans/codes that trigger `handleEntityClick(target)` on click.
   - When a user highlights text that spans across an `.inspectable` element, `window.getSelection()` returns a non-empty string.
   - When the user releases the mouse button, the click event bubbles to `clickHandler`.
   - Line 315 of `App.svelte` checks `sel && sel.toString().trim().length > 0`. Because text is highlighted, `clickHandler` immediately returns without executing `handleEntityClick(target)`.
   - As a result:
     - The Inspector Drawer does NOT open (`isDrawerOpen` remains false, `body` does NOT receive `.inspector-open`).
     - The `<AnnotationPopover>` is rendered and remains visible, allowing the user to select an annotation category and create a note.
   - Conversely, when the user clicks an `.inspectable` element without highlighting text (`sel.length === 0`), `handleEntityClick(target)` executes, opening the drawer directly to that entity's details.

4. **Annotation Creation & Preview**:
   - Selecting text triggers `selectionchange`, rendering `.annotation-popover`.
   - Clicking a category button puts the popover into composer mode (`isComposing = true`).
   - Typing into `textarea.composer-textarea` enables the "Preview" tab and the "Save Note" button.
   - Clicking "Preview" hides the textarea and displays `.composer-preview.markdown-body` with rendered HTML.
   - Clicking "Save Note" saves the note, closes the popover, creates `.md-annotation-mark` in the document, and adds the note to `AnnotationCard` in the Inspector Drawer's Review tab and Margin Gutter.

---

## 3. Comprehensive Selector & State Inventory for Playwright Automation

### Table 1: Exact DOM Selectors and Expected States

| UI Component | Purpose / Interaction | Exact DOM Selector | Expected State / Class / Content |
|---|---|---|---|
| **TableToolbar** | Container | `.table-toolbar-container` | Sibling directly preceding `table` |
| | Toolbar Root | `.table-toolbar-container .table-toolbar` | Visible, `aria-label="Table filter controls"` |
| | Category Pills Container | `.table-toolbar .category-pills` | Visible when categorical column detected |
| | "All" Pill Button | `.category-pills button.pill-btn:has-text("All")` | Text: `All (N)`, Class: `pill-btn active` |
| | Category Pill Button | `.category-pills button.pill-btn:has-text("<CAT>")` | Text: `<CAT> (Count)`, Class: `pill-btn` (or `.active`) |
| | Search Input Box | `.table-toolbar .search-box input[type="text"]` | Placeholder: `Filter table records...` |
| | Clear Search Button | `.table-toolbar .search-box button.clear-btn` | Visible only when `input.value !== ""` |
| | Count Badge | `.table-toolbar .toolbar-right .count-badge` | Text: `"<visible> / <total>"` (e.g. `"4 / 6"`) |
| | Table Rows (Visible) | `table tbody tr:visible` | Style `display: ""` |
| | Table Rows (Hidden) | `table tbody tr[style*="display: none"]` | Hidden in browser, restored on print |
| **HUD Ribbon** | Inspector Toggle Button | `#viewer-hud-ribbon button.action-btn:has-text("Inspector"), #viewer-hud-ribbon button.action-btn:has-text("Entities")` | Class: `action-btn` (has `.active` when open) |
| | Comments Count Badge | `#viewer-hud-ribbon button.action-btn:has-text("💬")` | Displays `💬 <count>` when annotations exist |
| | Educative Mode Toggle | `#viewer-hud-ribbon button.action-btn:has-text("Educative")` | Class: `action-btn active` (controls margin gutter) |
| **Inspector Drawer** | Drawer Root | `aside.drawer-container` | Visible, `aria-label="Entity Details Inspector"`, fixed right |
| | Body Class | `body.inspector-open` | Present when drawer open, absent when closed |
| | Drawer Close Button | `aside.drawer-container .drawer-header button.close-btn` | Text `✕`, aria-label `Close` |
| | Header Tabs Container | `aside.drawer-container .drawer-header .header-tab-bar` | Visible when `entity === null` |
| | Entities Tab Button | `.header-tab-bar button.header-tab-btn:has-text("Entities")` | Text: `📦 Entities (N)`, Class: `header-tab-btn active` |
| | Review Tab Button | `.header-tab-bar button.header-tab-btn:has-text("Review")` | Text: `💬 Review (N)`, Class: `header-tab-btn` |
| | Entity Search Input | `aside.drawer-container .search-box input.search-input` | Placeholder: `Search knowledge entities...` |
| | Entity Clear Button | `aside.drawer-container .search-box button.search-clear-btn` | Text `✕`, visible when search query typed |
| | Entity Category Pills | `aside.drawer-container .category-pills button.pill-btn` | Text: `All (N)`, `CVE (N)`, etc. Class: `.active` |
| | Entity Item Card | `aside.drawer-container .entity-cards-list .entity-item-card` | Role: `button`, child `.item-id` and `.item-title` |
| | Nav Back Button | `aside.drawer-container .drawer-header button.nav-back-btn` | Text: `← All Entities` (present in single detail mode) |
| | Entity Hero Card | `aside.drawer-container .entity-hero-card` | Has `h2.entity-title`, `.token-row code.entity-id` |
| | Copy Token Button | `aside.drawer-container .token-row button.copy-btn` | Text: `📋 Copy` |
| **Annotation Popover** | Popover Container | `.annotation-popover[role="dialog"]` | Fixed overlay above selected text range |
| | Action Bar | `.annotation-popover .popover-action-bar` | Visible in initial state (`!isComposing`) |
| | Category Buttons | `.popover-action-bar button.popover-btn` | Buttons with title `Add Comment`, `Add Correction`, etc. |
| | Popover Close Button | `.popover-action-bar button.popover-close-btn` | Text `✕` |
| | Composer Container | `.annotation-popover .popover-composer` | Visible when category clicked (`isComposing`) |
| | Author Input | `.popover-composer input.author-input` | Default value `"Reviewer"` |
| | Mode Tab: Write | `.popover-composer .composer-mode-bar button.mode-tab-btn:has-text("Write")` | Active when editing text |
| | Mode Tab: Preview | `.popover-composer .composer-mode-bar button.mode-tab-btn:has-text("Preview")` | Disabled when textarea empty, active in preview |
| | Quote Box | `.popover-composer .composer-quote` | Displays quoted text snippet |
| | Textarea | `.popover-composer textarea.composer-textarea` | Placeholder: `Add your note in Markdown...` |
| | Markdown Preview Pane | `.popover-composer .composer-preview.markdown-body` | Visible in preview mode, contains parsed tags |
| | Cancel Button | `.popover-composer .composer-actions button.btn-cancel` | Text `Back` |
| | Save Note Button | `.popover-composer .composer-actions button.btn-save` | Text `Save Note`, disabled if empty |
| **Annotation Display** | Highlight Mark | `mark.md-annotation-mark` | Class: `md-annotation-mark category-<cat>`, `data-ann-id` |
| | Margin Gutter Container | `aside.margin-gutter` | Visible when viewport >= 1280px & educativeMode active |
| | Annotation Card | `.annotation-card[role="article"]` | Child `.category-badge`, `.card-text.markdown-body` |
| | Card Edit Button | `.annotation-card button.action-icon-btn[title="Edit note"]` | Text `✏️` |
| | Card Delete Button | `.annotation-card button.action-icon-btn.delete-btn[title="Delete note"]` | Text `🗑️` |
| | Card Resolve Button | `.annotation-card button.action-icon-btn[title*="Resolved"]` | Text `✅` or `↩️` |
| **Inspectable Pills** | Inspectable Token | `.inspectable` | Element: `span.inspectable` or `code.inspectable`, `data-token` |

---

## 4. Playwright E2E Automation Recipes

Here are ready-to-implement Playwright test snippets for `tests/e2e/test_svelte_viewer.py`:

### Recipe 1: TableToolbar Search & Category Filtering
```python
async def test_table_toolbar_search_and_category(page):
    # 1. Locate toolbar preceding target table
    toolbar = page.locator(".table-toolbar-container .table-toolbar").first
    await expect(toolbar).to_be_visible()

    # 2. Check initial count badge
    badge = toolbar.locator(".toolbar-right .count-badge")
    await expect(badge).to_have_text(re.compile(r"^\d+\s*/\s*\d+$"))

    # 3. Click a category pill button (e.g. MALICIOUS)
    category_btn = toolbar.locator(".category-pills button.pill-btn:has-text('MALICIOUS')")
    if await category_btn.count() > 0:
        await category_btn.click()
        await expect(category_btn).to_have_class(re.compile(r"active"))
        # Check that matching rows remain visible and non-matching rows are hidden
        await expect(page.locator("table tbody tr:has-text('MALICIOUS')").first).to_be_visible()
        await expect(page.locator("table tbody tr:has-text('SUSPICIOUS')").first).to_be_hidden()

    # 4. Live search filtering
    search_input = toolbar.locator(".search-box input[type='text']")
    await search_input.fill("Credential")
    await expect(page.locator("table tbody tr:has-text('Credential')").first).to_be_visible()
    
    # 5. Clear filter button
    clear_btn = toolbar.locator(".search-box button.clear-btn")
    await expect(clear_btn).to_be_visible()
    await clear_btn.click()
    await expect(search_input).to_have_value("")
```

### Recipe 2: InspectorDrawer HUD Toggle, Search & Category Filter
```python
async def test_inspector_drawer_catalog_and_search(page):
    # 1. Open drawer from HUD ribbon
    hud_btn = page.locator("#viewer-hud-ribbon button.action-btn:has-text('Inspector'), #viewer-hud-ribbon button.action-btn:has-text('Entities')").first
    await hud_btn.click()

    drawer = page.locator("aside.drawer-container")
    await expect(drawer).to_be_visible()
    await expect(page.locator("body")).to_have_class(re.compile(r"inspector-open"))

    # 2. Filter entities via search
    search_input = drawer.locator(".search-box input.search-input")
    await search_input.fill("CVE-")
    cards = drawer.locator(".entity-cards-list .entity-item-card")
    await expect(cards.first).to_be_visible()

    # 3. Select entity to view details
    await cards.first.click()
    await expect(drawer.locator(".entity-hero-card")).to_be_visible()
    back_btn = drawer.locator(".drawer-header button.nav-back-btn")
    await expect(back_btn).to_be_visible()

    # 4. Navigate back to catalog and close drawer
    await back_btn.click()
    await expect(drawer.locator(".entity-cards-list")).to_be_visible()
    await drawer.locator(".drawer-header button.close-btn").click()
    await expect(drawer).to_be_hidden()
    await expect(page.locator("body")).not_to_have_class(re.compile(r"inspector-open"))
```

### Recipe 3: Interaction Disambiguation (`.inspectable` Click vs Text Selection)
```python
async def test_interaction_disambiguation(page):
    # Locate an inspectable pill
    pill = page.locator(".inspectable").first
    await expect(pill).to_be_visible()

    # Case 1: Pure click opens drawer
    await pill.click()
    drawer = page.locator("aside.drawer-container")
    await expect(drawer).to_be_visible()
    await expect(page.locator("body")).to_have_class(re.compile(r"inspector-open"))

    # Close drawer
    await drawer.locator(".drawer-header button.close-btn").click()
    await expect(drawer).to_be_hidden()

    # Case 2: Selecting text across .inspectable suppresses drawer opening and opens AnnotationPopover
    # Select text inside the inspectable element
    await page.evaluate("""() => {
        const el = document.querySelector('.inspectable');
        const range = document.createRange();
        range.selectNodeContents(el);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new Event('selectionchange'));
    }""")

    popover = page.locator(".annotation-popover")
    await expect(popover).to_be_visible()

    # Click the inspectable element while selection is active
    await pill.click()

    # Assertion: Drawer MUST remain closed, popover MUST remain open
    await expect(drawer).to_be_hidden()
    await expect(page.locator("body")).not_to_have_class(re.compile(r"inspector-open"))
    await expect(popover).to_be_visible()
```

### Recipe 4: Annotation Creation, Live Markdown Preview & Saving
```python
async def test_annotation_creation_and_preview(page):
    # 1. Trigger text selection within report content
    await page.evaluate("""() => {
        const target = document.querySelector('.report-content p, main p');
        const range = document.createRange();
        range.selectNodeContents(target);
        const sel = window.getSelection();
        sel.removeAllRanges();
        sel.addRange(range);
        document.dispatchEvent(new Event('selectionchange'));
    }""")

    popover = page.locator(".annotation-popover")
    await expect(popover).to_be_visible()

    # 2. Click category button (e.g. Comment)
    comment_btn = popover.locator(".popover-action-bar button.popover-btn[title='Add Comment']")
    await comment_btn.click()

    composer = popover.locator(".popover-composer")
    await expect(composer).to_be_visible()
    textarea = composer.locator("textarea.composer-textarea")
    save_btn = composer.locator("button.btn-save")
    await expect(save_btn).to_be_disabled()

    # 3. Enter markdown text
    await textarea.fill("Audit finding: **verified** with `payload.bin`.")
    await expect(save_btn).to_be_enabled()

    # 4. Switch to Preview tab
    preview_tab = composer.locator(".composer-mode-bar button.mode-tab-btn:has-text('Preview')")
    await preview_tab.click()
    preview_pane = composer.locator(".composer-preview.markdown-body")
    await expect(preview_pane).to_be_visible()
    await expect(preview_pane.locator("strong")).to_have_text("verified")
    await expect(preview_pane.locator("code")).to_have_text("payload.bin")
    await expect(textarea).to_be_hidden()

    # 5. Switch back to Write mode and save
    write_tab = composer.locator(".composer-mode-bar button.mode-tab-btn:has-text('Write')")
    await write_tab.click()
    await expect(textarea).to_be_visible()
    await save_btn.click()

    # Popover closes
    await expect(popover).to_be_hidden()

    # 6. Verify annotation badge in HUD updates
    await expect(page.locator("#viewer-hud-ribbon button.action-btn:has-text('💬 1')")).to_be_visible()
```

---

## 5. Caveats

1. **Margin Gutter Viewport Threshold**:
   - `MarginGutter.svelte:119-123` contains `@media (max-width: 1280px) { .margin-gutter { display: none !important; } }`.
   - Playwright tests asserting the visibility of cards in `.margin-gutter` must configure a viewport width of at least 1280px (e.g. 1920x1080).
2. **Text Selection Emulation**:
   - In headless Chromium, simulating drag-and-drop text selections via mouse coordinates can occasionally be flaky due to subpixel font metrics.
   - Using `document.createRange()`, `window.getSelection().addRange(range)`, and `document.dispatchEvent(new Event('selectionchange'))` via `page.evaluate()` provides 100% deterministic text selection triggers across all platforms.
3. **SVJ Housing Association Themes**:
   - `setupTableToolbars()` explicitly skips themes containing `theme-svj`. When testing `TableToolbar`, tests must use non-SVJ documents (e.g. `sample-forensic-cyber.html`, `school-report-sample.html`).

---

## 6. Conclusion

The technical investigation into the interactive Svelte viewer features confirms:
1. `TableToolbar.svelte` mounts automatically on non-SVJ tables with $\ge 4$ rows, auto-discovers categorical columns with 2 to 5 distinct values, and filters rows by toggling `display: none` while updating the `.count-badge`.
2. `InspectorDrawer.svelte` provides seamless navigation between a filterable knowledge catalog, single entity detail hero cards, and the review comments tab.
3. `AnnotationPopover.svelte` renders on selection within `.report-content`, supports 5 categories, offers live GFM Markdown preview via `marked` and `DOMPurify`, and persists notes via `annotationStore`.
4. Interaction disambiguation is implemented via `sel && sel.toString().trim().length > 0` in `clickHandler` (`App.svelte:315`), which guarantees that selecting text across `.inspectable` pills suppresses drawer opening and opens the annotation popover, while clean single-clicks open the entity drawer.

All exact DOM selectors, classes, and Playwright automation sequences have been compiled above.

---

## 7. Verification Method

To verify these observations independently:
1. Inspect `viewer/src/App.svelte:312-336` to verify the click handler disambiguation condition.
2. Inspect `viewer/src/TableToolbar.svelte:28-50` to verify the categorical column discovery heuristic.
3. Inspect `viewer/src/annotations/AnnotationPopover.svelte:84-122` to verify the Write/Preview mode tabs and live preview container.
4. Open `/home/valor/Devel/personal/md-style/examples/sample-forensic-cyber.html` in Chromium and inspect `.table-toolbar`, `.inspectable`, and `#viewer-hud-ribbon` elements.
