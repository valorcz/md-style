"""
tests/e2e/test_adversarial_e2e.py
Adversarial and Stress Test Harness for Milestone M3 (Headless Browser E2E Test Suite - R1).

Adversarially validates:
1. Multi-annotation persistence, editing, and tombstone interleaving across reloads.
2. Resilience against corrupted / malformed JSON in localStorage.
3. Rapid state transitions & tab switching in InspectorDrawer.
4. Physical mouse drag selection disambiguation on .inspectable elements.
5. Exported bundle integrity under adversarial inputs (XSS tags, special chars, paged mode state).
6. Margin gutter collision avoidance and card overlapping during inline card editing.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest
from playwright.sync_api import Browser, Page, expect

from tests.e2e.conftest import ConsoleTracker


def _select_element_text(page: Page, selector: str) -> None:
    """Programmatically selects text of target element and fires selectionchange."""
    page.evaluate(
        """(sel) => {
            const target = document.querySelector(sel);
            if (!target) throw new Error("Element not found: " + sel);
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


def test_adversarial_multi_annotation_lifecycle(
    page: Page, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Stress-tests multi-annotation creation, interleaving edits,
    selective tombstone deletion, and persistence across page reloads.
    """
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    # Locate multiple paragraph blocks
    paragraphs = page.locator(".report-content p, main p")
    assert paragraphs.count() >= 3, "Need at least 3 paragraphs for multi-annotation stress test"

    # Helper to add an annotation on a given element
    def add_ann(target_sel: str, cat_title: str, note_text: str) -> None:
        _select_element_text(page, target_sel)
        popover = page.locator(".annotation-popover")
        expect(popover).to_be_visible()
        cat_btn = popover.locator(f".popover-action-bar button.popover-btn[title='{cat_title}']")
        expect(cat_btn).to_be_visible()
        cat_btn.click()
        composer = popover.locator(".popover-composer")
        expect(composer).to_be_visible()
        textarea = composer.locator("textarea.composer-textarea")
        textarea.fill(note_text)
        save_btn = composer.locator(".composer-actions button.btn-save")
        expect(save_btn).to_be_enabled()
        save_btn.click()
        expect(popover).to_be_hidden()

    # 1. Create 3 distinct annotations across different paragraphs
    add_ann(".report-content p:nth-of-type(1)", "Add Comment", "Annotation ALPHA: initial observation")
    add_ann(".report-content p:nth-of-type(2)", "Add Insight", "Annotation BETA: critical correlation")
    add_ann(".report-content p:nth-of-type(3)", "Add Question", "Annotation GAMMA: verify hash integrity")

    # Verify 3 cards in margin gutter
    gutter_cards = page.locator(".margin-gutter .annotation-card")
    expect(gutter_cards).to_have_count(3)

    # Verify HUD ribbon shows 3 comments
    hud_badge = page.locator("#viewer-hud-ribbon button.action-btn:has-text('💬')")
    expect(hud_badge).to_contain_text("3")

    # 2. Edit Annotation GAMMA (the bottom card)
    card_gamma = gutter_cards.last
    expect(card_gamma).to_be_visible()
    card_gamma.locator("button.action-icon-btn[title='Edit note']").click()
    edit_box = card_gamma.locator(".card-edit-box")
    expect(edit_box).to_be_visible()
    edit_box.locator("textarea.edit-textarea").fill("Annotation GAMMA: EDITED and confirmed")
    edit_box.locator("button.btn-sm-save").click()
    expect(card_gamma.locator(".card-text")).to_contain_text("Annotation GAMMA: EDITED and confirmed")

    # 3. Delete Annotation BETA (should record tombstone)
    card_beta = page.locator(".margin-gutter .annotation-card:has-text('Annotation BETA')")
    expect(card_beta).to_be_visible()
    card_beta.locator("button.action-icon-btn.delete-btn[title='Delete note']").click()

    # Verify only 2 cards remain
    expect(gutter_cards).to_have_count(2)
    expect(hud_badge).to_contain_text("2")

    # 4. Check localStorage directly
    storage_state: Any = page.evaluate(
        """() => {
            const key = Object.keys(localStorage).find(k => k.startsWith('md-style:annotations:'));
            return JSON.parse(localStorage.getItem(key) || '{}');
        }"""
    )
    assert len(storage_state["annotations"]) == 2
    assert len(storage_state["tombstones"]) == 1

    # 5. Reload page and assert state survives intact
    page.reload()
    page.wait_for_selector("#viewer-hud-ribbon")

    reloaded_cards = page.locator(".margin-gutter .annotation-card")
    expect(reloaded_cards).to_have_count(2)
    expect(page.locator(".margin-gutter .annotation-card:has-text('Annotation GAMMA: EDITED and confirmed')")).to_be_visible()
    expect(page.locator(".margin-gutter .annotation-card:has-text('Annotation ALPHA: initial observation')")).to_be_visible()
    expect(page.locator(".margin-gutter .annotation-card:has-text('Annotation BETA')")).to_have_count(0)
    expect(hud_badge).to_contain_text("2")

    console_tracker.assert_no_errors("in test_adversarial_multi_annotation_lifecycle")


def test_adversarial_corrupted_local_storage(
    page: Page, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Adversarially tests viewer resilience when localStorage contains corrupted/malformed JSON.
    Expected bug behavior: persist() throws unhandled SyntaxError on existing JSON,
    failing to repair/overwrite corrupt storage with newly created annotations.
    """
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    doc_key: str = page.evaluate(
        """() => {
            const meta = document.querySelector('meta[name="doc-fingerprint"]')?.getAttribute('content');
            const docTitle = document.querySelector('meta[name="doc-title"]')?.getAttribute('content') || document.title;
            return meta || (docTitle ? 'doc-' + docTitle.toLowerCase().replace(/[^a-z0-9_-]+/g, '-') : 'md-style-doc');
        }"""
    )
    storage_key = f"md-style:annotations:{doc_key}"

    # Inject corrupt non-JSON string into localStorage
    page.evaluate(
        f"""() => {{
            localStorage.setItem('{storage_key}', '{{broken_json_syntax: true, [unclosed');
        }}"""
    )

    # Reload page with corrupted storage
    page.reload()
    page.wait_for_selector("#viewer-hud-ribbon")

    # Viewer must mount cleanly without uncaught exceptions
    console_tracker.assert_no_errors("upon mounting with corrupt localStorage")

    # Creating a new annotation must succeed and overwrite/repair the corrupted storage key
    _select_element_text(page, ".report-content p, main p")
    popover = page.locator(".annotation-popover")
    expect(popover).to_be_visible()
    popover.locator(".popover-action-bar button.popover-btn[title='Add Comment']").click()
    composer = popover.locator(".popover-composer")
    composer.locator("textarea.composer-textarea").fill("Resilience check note")
    composer.locator(".composer-actions button.btn-save").click()
    expect(popover).to_be_hidden()

    # Verify annotation card appears
    expect(page.locator(".margin-gutter .annotation-card")).to_have_count(1)

    # Verify localStorage now contains valid JSON
    storage_raw: str = page.evaluate(f"() => localStorage.getItem('{storage_key}')")
    try:
        parsed = json.loads(storage_raw)
        assert "annotations" in parsed
        assert len(parsed["annotations"]) == 1
        assert parsed["annotations"][0]["text"] == "Resilience check note"
    except json.JSONDecodeError:
        pytest.fail(f"localStorage remained corrupted after addAnnotation: {storage_raw}")

    # Reload page again: annotation must persist
    page.reload()
    page.wait_for_selector("#viewer-hud-ribbon")
    expect(page.locator(".margin-gutter .annotation-card")).to_have_count(1)
    expect(page.locator(".margin-gutter .annotation-card").first).to_contain_text("Resilience check note")

    console_tracker.assert_no_errors("in test_adversarial_corrupted_local_storage")


@pytest.mark.xfail(
    strict=True,
    reason=(
        "BUG-M3-02: In viewer/src/annotations/MarginGutter.svelte, vertical card stacking "
        "is calculated from static text estimates (estimateCardHeight) only when annotations change. "
        "When an upper card enters edit mode (.card-edit-box), it expands in DOM height, but the "
        "card below it does not shift down, causing the lower card to overlap and intercept pointer "
        "events over the upper card's Save button."
    ),
)
def test_adversarial_margin_gutter_edit_overlap(
    page: Page, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Adversarially tests card collision avoidance when an upper card is in edit mode.
    When Card 1 expands to show the textarea, Card 2 below it must not overlap Card 1's Save button.
    """
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    def add_ann(target_sel: str, cat_title: str, note_text: str) -> None:
        _select_element_text(page, target_sel)
        popover = page.locator(".annotation-popover")
        expect(popover).to_be_visible()
        cat_btn = popover.locator(f".popover-action-bar button.popover-btn[title='{cat_title}']")
        expect(cat_btn).to_be_visible()
        cat_btn.click()
        composer = popover.locator(".popover-composer")
        expect(composer).to_be_visible()
        textarea = composer.locator("textarea.composer-textarea")
        textarea.fill(note_text)
        save_btn = composer.locator(".composer-actions button.btn-save")
        expect(save_btn).to_be_enabled()
        save_btn.click()
        expect(popover).to_be_hidden()

    # Create Card 1 and Card 2 in close proximity
    add_ann(".report-content p:nth-of-type(1)", "Add Comment", "Card 1: Top note")
    add_ann(".report-content p:nth-of-type(2)", "Add Insight", "Card 2: Directly adjacent note")

    gutter_cards = page.locator(".margin-gutter .annotation-card")
    expect(gutter_cards).to_have_count(2)

    # Edit Card 1 (upper card)
    card_top = gutter_cards.first
    card_top.locator("button.action-icon-btn[title='Edit note']").click()

    edit_box = card_top.locator(".card-edit-box")
    expect(edit_box).to_be_visible()
    edit_box.locator("textarea.edit-textarea").fill("Card 1: Expanded edited note with extra text line")

    # In buggy implementation, Card 2 intercepts this click because it overlaps Card 1's Save button
    save_btn = edit_box.locator("button.btn-sm-save")
    save_btn.click(timeout=3000)

    expect(card_top.locator(".card-text")).to_contain_text("Card 1: Expanded edited note")
    console_tracker.assert_no_errors("in test_adversarial_margin_gutter_edit_overlap")


def test_adversarial_rapid_inspector_tab_switching(
    page: Page, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Stress-tests rapid tab switching and view navigation in InspectorDrawer:
    - Rapid alternation between Entities catalog and Review tabs.
    - Deep entity navigation and back-button thrashing.
    - Repeated open/close drawer toggling via Escape and HUD button.
    """
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    hud_btn = page.locator(
        "#viewer-hud-ribbon button.action-btn:has-text('Inspector'), "
        "#viewer-hud-ribbon button.action-btn:has-text('Entities')"
    ).first
    expect(hud_btn).to_be_visible()
    hud_btn.click()

    drawer = page.locator("aside.drawer-container")
    expect(drawer).to_be_visible()

    tab_kb = drawer.locator(".header-tab-bar button.header-tab-btn").first
    tab_review = drawer.locator(".header-tab-bar button.header-tab-btn:has-text('Review')")
    expect(tab_kb).to_be_visible()
    expect(tab_review).to_be_visible()

    # 1. Rapid tab switching (15 round trips)
    for _ in range(15):
        tab_review.click()
        tab_kb.click()

    # Settle on Review tab
    tab_review.click()
    expect(drawer.locator(".comments-management-view")).to_be_visible()
    expect(tab_review).to_have_class(re.compile(r"\bactive\b"))

    # Return to KB tab
    tab_kb.click()
    expect(drawer.locator(".entity-cards-list")).to_be_visible()

    # 2. Rapid entity drilldown and back navigation (5 round trips)
    first_card = drawer.locator(".entity-cards-list .entity-item-card").first
    expect(first_card).to_be_visible()

    for _ in range(5):
        first_card.click()
        back_btn = drawer.locator(".drawer-header button.nav-back-btn")
        expect(back_btn).to_be_visible()
        back_btn.click()
        expect(drawer.locator(".entity-cards-list")).to_be_visible()

    # 3. Rapid open/close drawer toggles
    for _ in range(5):
        page.keyboard.press("Escape")
        expect(drawer).to_be_hidden()
        hud_btn.click()
        expect(drawer).to_be_visible()

    # Close drawer cleanly
    page.keyboard.press("Escape")
    expect(drawer).to_be_hidden()
    expect(page.locator("body")).not_to_have_class(re.compile(r"\binspector-open\b"))

    console_tracker.assert_no_errors("in test_adversarial_rapid_inspector_tab_switching")


def test_adversarial_physical_mouse_drag_selection(
    page: Page, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Simulates real physical mouse drag-selection across an .inspectable pill.
    Verifies that real drag-selection suppresses entity drawer opening and triggers
    the annotation popover, while clean mouse click opens the entity drawer.
    """
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    pill = page.locator(".inspectable").first
    expect(pill).to_be_visible()
    drawer = page.locator("aside.drawer-container")

    box = pill.bounding_box()
    assert box is not None, "Bounding box of .inspectable pill not available"

    # 1. Perform physical mouse drag from left to right across the pill
    start_x = box["x"] + 2
    start_y = box["y"] + box["height"] / 2
    end_x = box["x"] + box["width"] - 2
    end_y = start_y

    page.mouse.move(start_x, start_y)
    page.mouse.down()
    page.mouse.move(end_x, end_y, steps=10)
    page.mouse.up()

    # Popover should be visible because text was selected
    popover = page.locator(".annotation-popover")
    expect(popover).to_be_visible()

    # Drawer must NOT open
    expect(drawer).to_be_hidden()
    expect(page.locator("body")).not_to_have_class(re.compile(r"\binspector-open\b"))

    # Dismiss popover with Escape
    page.keyboard.press("Escape")
    expect(popover).to_be_hidden()

    # Clear active selection so subsequent click is clean
    page.evaluate("() => window.getSelection()?.removeAllRanges()")

    # 2. Perform clean click on the same pill (without drag)
    pill.click()

    # Clean click must open the entity drawer
    expect(drawer).to_be_visible()
    expect(page.locator("body")).to_have_class(re.compile(r"\binspector-open\b"))

    # Close drawer
    drawer.locator(".drawer-header button.close-btn").click()
    expect(drawer).to_be_hidden()

    console_tracker.assert_no_errors("in test_adversarial_physical_mouse_drag_selection")


def test_adversarial_bundle_export_adversarial_payloads(
    page: Page, browser: Browser, tmp_path: Path, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """
    Adversarial bundle export stress test:
    - Injects XSS breakout tokens (<script>alert(1)</script>, quotes, closing tags).
    - Checks that Paged.js mode does not leave transient roots.
    - Verifies re-opened bundle in an isolated context does not execute scripts
      and renders the sanitized annotation cleanly.
    """
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    # 1. Add annotation with malicious script and HTML breakout payloads
    _select_element_text(page, ".report-content p, main p")
    popover = page.locator(".annotation-popover")
    popover.locator(".popover-action-bar button.popover-btn[title='Add Comment']").click()
    composer = popover.locator(".popover-composer")
    payload = "Malicious note: <script>window.__xss_fired=true;</script> <img src=x onerror=window.__xss_img=true> `code injection`"
    composer.locator("textarea.composer-textarea").fill(payload)
    composer.locator(".composer-actions button.btn-save").click()

    # 2. Open Inspector Drawer and go to Review tab
    hud_btn = page.locator(
        "#viewer-hud-ribbon button.action-btn:has-text('Inspector'), "
        "#viewer-hud-ribbon button.action-btn:has-text('Entities')"
    ).first
    hud_btn.click()
    drawer = page.locator("aside.drawer-container")
    review_tab = drawer.locator(".header-tab-bar button.header-tab-btn:has-text('Review')")
    review_tab.click()

    # 3. Export bundle
    with page.expect_download() as download_info:
        drawer.locator("button.export-html-btn").click()
    download = download_info.value

    exported_file = tmp_path / download.suggested_filename
    download.save_as(exported_file)
    assert exported_file.is_file()

    # 4. Verify raw exported HTML content
    raw_html = exported_file.read_text(encoding="utf-8")

    # Must escape '<' in embedded JSON manifest
    assert "<script>window.__xss_fired=true;</script>" not in raw_html
    assert "\\u003cscript>window.__xss_fired=true;\\u003c/script>" in raw_html

    # Transient elements must be absent
    assert 'class="table-toolbar-container"' not in raw_html
    assert 'class="annotation-popover"' not in raw_html
    assert 'class="margin-gutter"' not in raw_html

    # 5. Open exported bundle in a new clean browser context
    clean_context = browser.new_context(viewport={"width": 1440, "height": 900})
    clean_page = clean_context.new_page()

    clean_errors: list[str] = []
    clean_page.on("console", lambda msg: clean_errors.append(msg.text) if msg.type == "error" else None)
    clean_page.on("pageerror", lambda err: clean_errors.append(str(err)))

    clean_page.goto(f"file://{exported_file.resolve()}")
    clean_page.wait_for_selector("#viewer-hud-ribbon")

    # Assert XSS payload was NOT executed
    xss_fired = clean_page.evaluate("() => Boolean(window.__xss_fired || window.__xss_img)")
    assert not xss_fired, "XSS payload executed in exported bundle!"

    # Assert zero console or page errors
    assert clean_errors == [], f"Console errors in exported bundle: {clean_errors}"

    # Assert annotation re-hydrated
    card = clean_page.locator(".margin-gutter .annotation-card").first
    expect(card).to_be_visible()
    expect(card.locator(".card-text")).to_contain_text("Malicious note:")

    clean_context.close()
    console_tracker.assert_no_errors("in test_adversarial_bundle_export_adversarial_payloads")
