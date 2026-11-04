"""
tests/e2e/test_toc_and_declutter.py
E2E Playwright tests for HUD Top Bar Decluttering and Left Collapsible Table of Contents.
"""

from pathlib import Path
import re
import pytest
from playwright.sync_api import Page, expect

from e2e.conftest import ConsoleTracker


def test_hud_declutter_and_more_menu(
    page: Page, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """Verifies decluttered HUD top bar and '···' More Actions popover menu."""
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    # 1. ToC button is visible on the left
    toc_btn = page.locator("#viewer-hud-ribbon button.toc-btn")
    expect(toc_btn).to_be_visible()

    # 2. Entity and Notes buttons are compact badge pills
    entity_btn = page.locator("#viewer-hud-ribbon button.action-btn:has-text('Entities')")
    expect(entity_btn).to_be_visible()

    notes_btn = page.locator("#viewer-hud-ribbon button.action-btn:has-text('Notes')")
    expect(notes_btn).to_be_visible()

    # 3. Segmented control [ Web | Paper ]
    segmented = page.locator("#viewer-hud-ribbon .segmented-control")
    expect(segmented).to_be_visible()
    expect(segmented.locator("button.segmented-item:has-text('Web')")).to_be_visible()
    expect(segmented.locator("button.segmented-item:has-text('Paper')")).to_be_visible()

    # 4. More actions popover toggle
    more_btn = page.locator("#viewer-hud-ribbon button.more-btn")
    expect(more_btn).to_be_visible()

    menu = page.locator("#viewer-hud-ribbon .more-dropdown-menu")
    expect(menu).to_be_hidden()

    # Click more button to reveal popover
    more_btn.click()
    expect(menu).to_be_visible()
    expect(menu.locator(".dropdown-item:has-text('Mode')")).to_be_visible()
    expect(menu.locator(".dropdown-item:has-text('Print')")).to_be_visible()

    # Click outside to dismiss menu
    page.locator("body").click(position={"x": 500, "y": 200})
    expect(menu).to_be_hidden()

    console_tracker.assert_no_errors("in test_hud_declutter_and_more_menu")


def test_sidebar_toc_toggle_and_navigation(
    page: Page, sample_cyber_html: Path, console_tracker: ConsoleTracker
) -> None:
    """Verifies opening left ToC, depth switcher, scrolling to section, and closing."""
    page.goto(f"file://{sample_cyber_html.resolve()}")
    page.wait_for_selector("#viewer-hud-ribbon")

    toc = page.locator("aside.sidebar-toc")
    expect(toc).not_to_have_class(re.compile(r"\bis-open\b"))

    # 1. Click ToC button on HUD ribbon
    toc_btn = page.locator("#viewer-hud-ribbon button.toc-btn")
    toc_btn.click()
    expect(toc).to_have_class(re.compile(r"\bis-open\b"))
    expect(page.locator("body")).to_have_class(re.compile(r"\btoc-docked\b"))

    # Backdrop should be hidden on desktop (non-modal dock, no blur)
    backdrop = page.locator(".sidebar-toc-backdrop")
    expect(backdrop).to_be_hidden()

    # Document content remains visible and not blurred
    doc_heading = page.locator("main h1, .report-content h1").first
    expect(doc_heading).to_be_visible()

    # Unified canvas test: in web view, body has no drop shadow or artificial paper border
    body_styles = page.evaluate("""() => {
        const bodyStyle = window.getComputedStyle(document.body);
        const htmlStyle = window.getComputedStyle(document.documentElement);
        return {
            bodyBoxShadow: bodyStyle.boxShadow,
            bodyBg: bodyStyle.backgroundColor,
            htmlBg: htmlStyle.backgroundColor,
        };
    }""")
    assert body_styles["bodyBoxShadow"] == "none"
    assert body_styles["bodyBg"] == body_styles["htmlBg"]

    # 2. Check headings in ToC list (clean semantic tree, no ul/li bullet markers)
    assert toc.locator("ul, li").count() == 0
    # No redundant "Obsah" header title
    assert toc.locator(".toc-heading").count() == 0

    toc_links = toc.locator(".toc-link")
    assert toc_links.count() > 0

    # Verify no text-decoration underline on ToC links
    first_link_decor = page.evaluate("() => window.getComputedStyle(document.querySelector('.sidebar-toc .toc-link')).textDecorationLine")
    assert first_link_decor == "none"

    # Spine styling check: text should be right-aligned toward the document
    if "is-spine" in (toc.get_attribute("class") or ""):
        first_align = page.evaluate("() => window.getComputedStyle(document.querySelector('.sidebar-toc .toc-link')).textAlign")
        assert first_align == "right"
        # Spine z-index should be 10 (so wide figures with z-index 20 float over it)
        spine_z = page.evaluate("() => window.getComputedStyle(document.querySelector('.sidebar-toc.is-spine')).zIndex")
        assert spine_z == "10"

    # 3. Dynamic depth filter buttons (e.g. h1, h2, h3)
    pills = toc.locator("button.depth-pill")
    if pills.count() > 0:
        first_pill = pills.first
        first_pill.click()
        expect(first_pill).to_have_class(re.compile(r"\bis-active\b"))

    # 4. Click first heading link to scroll
    first_link = toc.locator(".toc-link").first
    target_id = first_link.get_attribute("data-id")
    assert target_id is not None
    first_link.click()

    # 5. Close button
    close_btn = toc.locator("button.toc-close-btn")
    close_btn.click()
    expect(toc).not_to_have_class(re.compile(r"\bis-open\b"))

    # 6. Keyboard shortcut 't' to open and 'Escape' to close
    page.keyboard.press("t")
    expect(toc).to_have_class(re.compile(r"\bis-open\b"))

    page.keyboard.press("Escape")
    expect(toc).not_to_have_class(re.compile(r"\bis-open\b"))

    # 7. Entity hover card test
    inspectable = page.locator(".inspectable").first
    if inspectable.count() > 0:
        inspectable.hover()
        hover_card = page.locator(".entity-hover-card")
        expect(hover_card).to_be_visible()
        expect(hover_card.locator(".card-title")).to_be_visible()
        expect(hover_card.locator(".card-action-btn")).to_be_visible()

    console_tracker.assert_no_errors("in test_sidebar_toc_toggle_and_navigation")
