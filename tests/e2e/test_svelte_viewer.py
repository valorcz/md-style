"""
tests/e2e/test_svelte_viewer.py
Comprehensive Playwright End-to-End Test Suite for interactive Svelte Viewer.

Milestone: M3 (Headless Browser E2E Test Suite - R1).
Coverage:
- Feature 18: TableToolbar search, category pill filtering, row hiding, count badge.
- Feature 19: InspectorDrawer entity catalog, search, category filtering, detail hero card, back navigation.
- Feature 20: Interaction disambiguation between .inspectable pills and text selection.
- Feature 21: Annotation lifecycle, popover category tagging, live Markdown preview, and DOM/HUD updates.
- Feature 22: LocalStorage persistence across page reloads and card editing.
- Feature 22: Tombstone deletion mechanics preventing resurrection.
- Feature 23: Embedded script tag (#md-style-annotations) re-hydration and tombstone override.
- Feature 24: Clean bundle export (exportUpdatedHtmlBundle) stripping transient roots and re-hydrating with 0 console errors.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

from playwright.sync_api import Browser, Page, expect

from tests.e2e.conftest import ConsoleTracker


def _trigger_text_selection(page: Page, selector: str = ".report-content p, main p") -> None:
    """Helper to programmatically select text within the document content."""
    page.evaluate(
        """(sel) => {
            const target = document.querySelector(sel);
            if (!target) throw new Error("Target text container not found: " + sel);
            const node = target.firstChild || target;
            const range = document.createRange();
            range.selectNodeContents(node);
            const selObj = window.getSelection();
            if (selObj) {
                selObj.removeAllRanges();
                selObj.addRange(range);
            }
            document.dispatchEvent(new Event('selectionchange'));
        }""",
        selector,
    )


def test_table_toolbar_filtering_and_search(
    page: Page, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Feature 18: TableToolbar.svelte
    Verifies that category pills filter table rows via display: none,
    the count-badge updates dynamically ({visible} / {total}),
    the live search box filters rows by text, and clear button resets the filter.
    """
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    # 1. Locate toolbar preceding target table
    toolbar = page.locator(".table-toolbar-container .table-toolbar").first
    expect(toolbar).to_be_visible()

    # 2. Check initial count badge format (e.g. "7 / 7")
    badge = toolbar.locator(".toolbar-right .count-badge")
    expect(badge).to_have_text(re.compile(r"^\d+\s*/\s*\d+$"))
    initial_text = badge.inner_text().strip()
    total_rows = int(initial_text.split("/")[1].strip())
    assert total_rows > 0

    # 3. Category pill filtering
    pills = toolbar.locator(".category-pills button.pill-btn")
    if pills.count() > 1:
        # Click a specific category pill (second button after "All")
        category_btn = pills.nth(1)
        category_text = category_btn.inner_text()
        category_name = category_text.split("(")[0].strip()
        category_btn.click()

        # Verify active class on clicked pill
        expect(category_btn).to_have_class(re.compile(r"\bactive\b"))

        # Verify count badge updated and is less than or equal to total
        updated_badge = badge.inner_text().strip()
        visible_count = int(updated_badge.split("/")[0].strip())
        assert visible_count <= total_rows

        # Click "All" pill button to restore all rows
        all_btn = pills.first
        all_btn.click()
        expect(all_btn).to_have_class(re.compile(r"\bactive\b"))
        expect(badge).to_have_text(initial_text)

    # 4. Live search input filtering
    search_input = toolbar.locator(".search-box input[type='text']")
    expect(search_input).to_be_visible()

    # Find text from the first table row to use as query
    first_row = page.locator("table tbody tr").first
    row_text = first_row.inner_text()
    search_word = row_text.split()[0] if row_text.split() else "a"

    search_input.fill(search_word)
    # Clear button should become visible when search query is entered
    clear_btn = toolbar.locator(".search-box button.clear-btn")
    expect(clear_btn).to_be_visible()

    # Verify matching rows remain visible
    expect(page.locator(f"table tbody tr:has-text('{search_word}')").first).to_be_visible()

    # Click clear button to reset search filter
    clear_btn.click()
    expect(search_input).to_have_value("")
    expect(clear_btn).to_be_hidden()
    expect(badge).to_have_text(initial_text)

    console_tracker.assert_no_errors("in test_table_toolbar_filtering_and_search")


def test_inspector_drawer_catalog_and_filtering(
    page: Page, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Feature 19: InspectorDrawer.svelte
    Verifies that the Inspector Drawer opens via HUD button,
    entity search filters cards, category pills filter types,
    and clicking an entity transitions to the Detail View with hero card
    and back button returns to the catalog.
    """
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    # 1. Open drawer from HUD ribbon
    hud_btn = page.locator(
        "#viewer-hud-ribbon button.action-btn:has-text('Inspector'), "
        "#viewer-hud-ribbon button.action-btn:has-text('Entities')"
    ).first
    expect(hud_btn).to_be_visible()
    hud_btn.click()

    drawer = page.locator("aside.drawer-container")
    expect(drawer).to_be_visible()
    expect(page.locator("body")).to_have_class(re.compile(r"\binspector-open\b"))

    # 2. Filter entities via live search
    search_input = drawer.locator(".search-box input.search-input")
    expect(search_input).to_be_visible()
    search_input.fill("CVE-")

    cards = drawer.locator(".entity-cards-list .entity-item-card")
    expect(cards.first).to_be_visible()
    expect(cards.first).to_contain_text("CVE-")

    # Clear search
    clear_search_btn = drawer.locator(".search-box button.search-clear-btn")
    expect(clear_search_btn).to_be_visible()
    clear_search_btn.click()
    expect(search_input).to_have_value("")

    # 3. Category pills in drawer
    category_pills = drawer.locator(".category-pills button.pill-btn")
    if category_pills.count() > 1:
        # Click a category pill
        cve_pill = category_pills.filter(has_text="CVE")
        if cve_pill.count() > 0:
            cve_pill.first.click()
            expect(cve_pill.first).to_have_class(re.compile(r"\bactive\b"))

    # 4. Click first entity card to enter Single Entity Detail View
    first_card = drawer.locator(".entity-cards-list .entity-item-card").first
    expect(first_card).to_be_visible()
    first_card.click()

    # Verify Single Entity Detail View
    hero_card = drawer.locator(".entity-hero-card")
    expect(hero_card).to_be_visible()
    back_btn = drawer.locator(".drawer-header button.nav-back-btn")
    expect(back_btn).to_be_visible()

    # 5. Navigate back to Catalog Browser View
    back_btn.click()
    expect(drawer.locator(".entity-cards-list")).to_be_visible()
    expect(hero_card).to_be_hidden()

    # 6. Close drawer
    close_btn = drawer.locator(".drawer-header button.close-btn")
    close_btn.click()
    expect(drawer).to_be_hidden()
    expect(page.locator("body")).not_to_have_class(re.compile(r"\binspector-open\b"))

    console_tracker.assert_no_errors("in test_inspector_drawer_catalog_and_filtering")


def test_inspectable_pill_selection_disambiguation(
    page: Page, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Feature 20: Interaction Disambiguation
    Verifies that clean single-click on an .inspectable pill opens the Inspector Drawer,
    whereas text selection across an .inspectable pill suppresses drawer opening
    and triggers the .annotation-popover.
    """
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    pill = page.locator(".inspectable").first
    expect(pill).to_be_visible()

    # Case 1: Clean click opens the entity drawer
    pill.click()
    drawer = page.locator("aside.drawer-container")
    expect(drawer).to_be_visible()
    expect(page.locator("body")).to_have_class(re.compile(r"\binspector-open\b"))

    # Close drawer
    drawer.locator(".drawer-header button.close-btn").click()
    expect(drawer).to_be_hidden()
    expect(page.locator("body")).not_to_have_class(re.compile(r"\binspector-open\b"))

    # Case 2: Selecting text across .inspectable suppresses drawer and shows popover
    _trigger_text_selection(page, ".inspectable")

    popover = page.locator(".annotation-popover")
    expect(popover).to_be_visible()

    # Dispatch click event on the pill while text selection is active
    # (simulates mouseup/click at the conclusion of drag-selecting across an inspectable element)
    page.evaluate(
        """() => {
            const el = document.querySelector('.inspectable');
            if (el) {
                el.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
            }
        }"""
    )

    # Assertion: Drawer must remain closed, popover must remain open
    expect(drawer).to_be_hidden()
    expect(page.locator("body")).not_to_have_class(re.compile(r"\binspector-open\b"))
    expect(popover).to_be_visible()

    # Cancel popover via Escape key
    page.keyboard.press("Escape")
    expect(popover).to_be_hidden()

    console_tracker.assert_no_errors("in test_inspectable_pill_selection_disambiguation")


def test_annotation_lifecycle_and_markdown_preview(
    page: Page, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Feature 21: Annotation Lifecycle & Live Markdown Preview
    Verifies text selection within report content, category tagging,
    composer with Write/Preview tabs, live markdown rendering,
    and saving the annotation to the DOM and HUD badge.
    """
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    # 1. Trigger text selection within report content
    _trigger_text_selection(page, ".report-content p, main p")

    popover = page.locator(".annotation-popover")
    expect(popover).to_be_visible()

    # 2. Select category button (Comment)
    comment_btn = popover.locator(".popover-action-bar button.popover-btn[title='Add Comment']")
    expect(comment_btn).to_be_visible()
    comment_btn.click()

    composer = popover.locator(".popover-composer")
    expect(composer).to_be_visible()
    textarea = composer.locator("textarea.composer-textarea")
    save_btn = composer.locator(".composer-actions button.btn-save")

    # Save button must be disabled when textarea is empty
    expect(save_btn).to_be_disabled()

    # 3. Fill markdown note
    note_markdown = "Audit finding: **verified** with `payload.bin`."
    textarea.fill(note_markdown)
    expect(save_btn).to_be_enabled()

    # 4. Switch to Preview tab
    preview_tab = composer.locator(".composer-mode-bar button.mode-tab-btn:has-text('Preview')")
    expect(preview_tab).to_be_visible()
    preview_tab.click()

    preview_pane = composer.locator(".composer-preview.markdown-body")
    expect(preview_pane).to_be_visible()
    expect(preview_pane.locator("strong")).to_have_text("verified")
    expect(preview_pane.locator("code")).to_have_text("payload.bin")
    expect(textarea).to_be_hidden()

    # 5. Switch back to Write mode and save
    write_tab = composer.locator(".composer-mode-bar button.mode-tab-btn:has-text('Write')")
    write_tab.click()
    expect(textarea).to_be_visible()
    expect(preview_pane).to_be_hidden()

    save_btn.click()
    expect(popover).to_be_hidden()

    # 6. Verify annotation card rendered in Margin Gutter (desktop viewport >= 1280px)
    gutter_card = page.locator(".margin-gutter .annotation-card").first
    expect(gutter_card).to_be_visible()
    expect(gutter_card.locator(".card-text")).to_contain_text("Audit finding: verified with payload.bin")

    # 7. Verify HUD ribbon comment badge updated
    hud_comment_badge = page.locator("#viewer-hud-ribbon button.action-btn:has-text('💬')")
    expect(hud_comment_badge).to_be_visible()
    expect(hud_comment_badge).to_contain_text("1")

    console_tracker.assert_no_errors("in test_annotation_lifecycle_and_markdown_preview")


def test_storage_persistence_and_card_editing(
    page: Page, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Feature 22: LocalStorage Persistence & Card Editing
    Verifies that creating an annotation, editing its note content via the card UI,
    persists in localStorage key md-style:annotations:{docKey} and survives page reload.
    """
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    # 1. Create an annotation
    _trigger_text_selection(page, ".report-content p, main p")
    popover = page.locator(".annotation-popover")
    popover.locator(".popover-action-bar button.popover-btn[title='Add Comment']").click()
    composer = popover.locator(".popover-composer")
    composer.locator("textarea.composer-textarea").fill("Initial triage note")
    composer.locator(".composer-actions button.btn-save").click()
    expect(popover).to_be_hidden()

    # 2. Verify card in margin gutter
    gutter_card = page.locator(".margin-gutter .annotation-card").first
    expect(gutter_card).to_be_visible()
    expect(gutter_card.locator(".card-text")).to_contain_text("Initial triage note")

    # 3. Edit annotation via card pencil button
    edit_btn = gutter_card.locator("button.action-icon-btn[title='Edit note']")
    expect(edit_btn).to_be_visible()
    edit_btn.click()

    edit_box = gutter_card.locator(".card-edit-box")
    expect(edit_box).to_be_visible()
    edit_textarea = edit_box.locator("textarea.edit-textarea")
    edit_textarea.fill("Updated reviewed finding: **critical**")
    edit_box.locator("button.btn-sm-save").click()

    # Assert edited text is updated in the card DOM
    expect(gutter_card.locator(".card-text")).to_contain_text("Updated reviewed finding: critical")

    # 4. Verify localStorage schema
    storage_data: Any = page.evaluate(
        """() => {
            const key = Object.keys(localStorage).find(k => k.startsWith('md-style:annotations:'));
            return key ? JSON.parse(localStorage.getItem(key) || '{}') : null;
        }"""
    )
    assert storage_data is not None, "localStorage annotation entry not found"
    assert "annotations" in storage_data
    assert "tombstones" in storage_data
    assert len(storage_data["annotations"]) == 1
    assert "critical" in storage_data["annotations"][0]["text"]

    # 5. Reload page and assert persistence across reload
    page.reload()
    page.wait_for_selector("#viewer-hud-ribbon")

    reloaded_card = page.locator(".margin-gutter .annotation-card").first
    expect(reloaded_card).to_be_visible()
    expect(reloaded_card.locator(".card-text")).to_contain_text("Updated reviewed finding: critical")

    console_tracker.assert_no_errors("in test_storage_persistence_and_card_editing")


def test_tombstone_deletion_persistence(
    page: Page, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Feature 22: Tombstone Deletion Mechanics
    Verifies that deleting an annotation appends its ID to tombstones in localStorage
    and prevents resurrection across page reloads.
    """
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    # 1. Create an annotation
    _trigger_text_selection(page, ".report-content p, main p")
    popover = page.locator(".annotation-popover")
    popover.locator(".popover-action-bar button.popover-btn[title='Add Insight']").click()
    composer = popover.locator(".popover-composer")
    composer.locator("textarea.composer-textarea").fill("Temporary insight to be deleted")
    composer.locator(".composer-actions button.btn-save").click()

    card = page.locator(".margin-gutter .annotation-card").first
    expect(card).to_be_visible()

    # Get created annotation ID from localStorage
    ann_id: str = page.evaluate(
        """() => {
            const key = Object.keys(localStorage).find(k => k.startsWith('md-style:annotations:'));
            const data = JSON.parse(localStorage.getItem(key) || '{}');
            return data.annotations[0].id;
        }"""
    )
    assert ann_id.startswith("ann-")

    # 2. Click Delete button on card
    delete_btn = card.locator("button.action-icon-btn.delete-btn[title='Delete note']")
    expect(delete_btn).to_be_visible()
    delete_btn.click()

    # Card must disappear from DOM
    expect(page.locator(".margin-gutter .annotation-card")).to_have_count(0)

    # 3. Assert localStorage state: annotations empty, tombstones contains ann_id
    storage_data: Any = page.evaluate(
        """() => {
            const key = Object.keys(localStorage).find(k => k.startsWith('md-style:annotations:'));
            return JSON.parse(localStorage.getItem(key) || '{}');
        }"""
    )
    assert len(storage_data["annotations"]) == 0
    assert ann_id in storage_data["tombstones"]

    # 4. Reload page and assert annotation remains suppressed
    page.reload()
    page.wait_for_selector("#viewer-hud-ribbon")
    expect(page.locator(".margin-gutter .annotation-card")).to_have_count(0)

    console_tracker.assert_no_errors("in test_tombstone_deletion_persistence")


def test_script_tag_rehydration_and_tombstone_override(
    page: Page, sample_annotated_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Feature 23: Embedded Script Tag Re-hydration & Tombstone Overrides
    Verifies that annotations pre-baked in <script id="md-style-annotations"> re-hydrate
    into the Svelte store and gutter on cold load, and that deleting an embedded annotation
    creates a tombstone that overrides and suppresses the item across reload.
    """
    # Open sample report with 2 pre-baked annotations
    page.goto(f"file://{sample_annotated_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    # 1. Assert both pre-baked annotations re-hydrated from script tag
    gutter_cards = page.locator(".margin-gutter .annotation-card")
    expect(gutter_cards).to_have_count(2)

    # 2. Delete "Note to be deleted via tombstone"
    target_card = page.locator(".margin-gutter .annotation-card:has-text('Note to be deleted via tombstone')")
    expect(target_card).to_be_visible()
    target_card.locator("button.action-icon-btn.delete-btn[title='Delete note']").click()

    # Only 1 card remains visible
    expect(gutter_cards).to_have_count(1)
    expect(gutter_cards.first).to_contain_text("Initial triage confirmation")

    # 3. Verify tombstone stored in localStorage
    storage_data: Any = page.evaluate(
        """() => {
            const key = Object.keys(localStorage).find(k => k.startsWith('md-style:annotations:'));
            return JSON.parse(localStorage.getItem(key) || '{}');
        }"""
    )
    assert "ann-prebaked-2" in storage_data["tombstones"]

    # 4. Reload page
    page.reload()
    page.wait_for_selector("#viewer-hud-ribbon")

    # Crucial assertion: despite static HTML containing both annotations in #md-style-annotations,
    # the tombstone in localStorage overrides and suppresses the deleted annotation.
    expect(page.locator(".margin-gutter .annotation-card")).to_have_count(1)
    expect(page.locator(".margin-gutter .annotation-card").first).to_contain_text("Initial triage confirmation")

    console_tracker.assert_no_errors("in test_script_tag_rehydration_and_tombstone_override")


def test_clean_bundle_export_and_rehydration(
    page: Page, browser: Browser, tmp_path: Path, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Feature 24: Clean Bundle Export & Zero Console Error Re-hydration
    Verifies that clicking 'Export HTML Bundle' downloads an updated HTML file that:
    1. Strips all transient Svelte UI roots (#md-style-viewer-root, .table-toolbar-container, .margin-gutter).
    2. Embeds updated annotations in #md-style-annotations with escaped '<' characters (\\u003c).
    3. Re-opens in an isolated browser context with ZERO console errors or page errors.
    4. Automatically re-hydrates all annotations into the Svelte viewer.
    """
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    # 1. Create an annotation with Markdown and script tag test characters
    _trigger_text_selection(page, ".report-content p, main p")
    popover = page.locator(".annotation-popover")
    popover.locator(".popover-action-bar button.popover-btn[title='Add Praise']").click()
    composer = popover.locator(".popover-composer")
    composer.locator("textarea.composer-textarea").fill("Bundle export comment: **verified** <script>alert(1)</script>")
    composer.locator(".composer-actions button.btn-save").click()
    expect(popover).to_be_hidden()

    # 2. Open Inspector Drawer from HUD ribbon and navigate to Review tab
    hud_btn = page.locator(
        "#viewer-hud-ribbon button.action-btn:has-text('Inspector'), "
        "#viewer-hud-ribbon button.action-btn:has-text('Entities')"
    ).first
    hud_btn.click()
    drawer = page.locator("aside.drawer-container")
    expect(drawer).to_be_visible()

    review_tab = drawer.locator(".header-tab-bar button.header-tab-btn:has-text('Review')")
    expect(review_tab).to_be_visible()
    review_tab.click()

    export_btn = drawer.locator("button.export-html-btn")
    expect(export_btn).to_be_visible()

    # 3. Trigger download of updated bundle
    with page.expect_download() as download_info:
        export_btn.click()
    download = download_info.value

    exported_file = tmp_path / download.suggested_filename
    download.save_as(exported_file)
    assert exported_file.is_file() and exported_file.stat().st_size > 0

    # 4. Static assertions on raw exported HTML content
    raw_html = exported_file.read_text(encoding="utf-8")

    # Transient UI containers must be absent from exported HTML DOM
    assert 'class="table-toolbar-container"' not in raw_html, "Transient table toolbar found in exported HTML"
    assert 'class="annotation-popover"' not in raw_html, "Transient annotation popover found in exported HTML"
    assert 'class="margin-gutter"' not in raw_html, "Transient margin gutter found in exported HTML"
    assert 'class="md-annotation-mark"' not in raw_html, "Unwrapped highlight mark tags found in exported HTML"

    # Mounting container must be cleanly present
    assert '<div id="md-style-viewer-root"></div>' in raw_html, "Missing clean viewer root in exported bundle"

    # Embedded script tag must be present with sanitized '<' escaping
    assert '<script id="md-style-annotations" type="application/json">' in raw_html
    assert "\\u003cscript>alert(1)" in raw_html, "Script breakout character was not escaped to \\u003c"
    assert "\\u003c/script>" in raw_html, "Closing script tag was not escaped to \\u003c/script>"

    # 5. Re-open exported HTML in a fresh, isolated browser context (clean localStorage)
    clean_context = browser.new_context(viewport={"width": 1440, "height": 900})
    clean_page = clean_context.new_page()

    intercepted_errors: list[str] = []
    intercepted_page_errors: list[str] = []
    clean_page.on("console", lambda msg: intercepted_errors.append(f"[{msg.type}] {msg.text}") if msg.type == "error" else None)
    clean_page.on("pageerror", lambda err: intercepted_page_errors.append(str(err)))

    clean_page.goto(f"file://{exported_file.resolve()}")
    clean_page.wait_for_selector("#viewer-hud-ribbon")

    # Assert ZERO console errors and ZERO page errors upon re-opening exported bundle
    assert intercepted_errors == [], f"Unexpected console errors in exported bundle: {intercepted_errors}"
    assert intercepted_page_errors == [], f"Unexpected uncaught page errors in exported bundle: {intercepted_page_errors}"

    # Assert full annotation visibility in clean context
    rehydrated_card = clean_page.locator(".margin-gutter .annotation-card").first
    expect(rehydrated_card).to_be_visible()
    expect(rehydrated_card.locator(".card-text")).to_contain_text("Bundle export comment: verified")

    clean_context.close()
    console_tracker.assert_no_errors("in test_clean_bundle_export_and_rehydration")
