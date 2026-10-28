"""
scripts/generate_preview_screenshots.py
Automated high-DPI screenshot generator for documentation and README preview assets.
Uses Playwright to capture pixel-perfect previews across interactive themes.
"""

import sys
from pathlib import Path
from playwright.sync_api import sync_playwright

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "docs" / "images"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

def generate_screenshots():
    cyber_html = Path("/tmp/sample-forensic-cyber.html").resolve()
    academic_html = Path("/tmp/sample-lecture-fi-muni.html").resolve()
    svj_html = Path("/tmp/pozvanka-svj.html").resolve()

    if not cyber_html.exists() or not academic_html.exists() or not svj_html.exists():
        print("Error: Missing compiled HTML samples in /tmp. Run md-style compilation first.")
        sys.exit(1)

    with sync_playwright() as p:
        browser = p.chromium.launch(
            headless=True,
            args=["--no-sandbox", "--disable-gpu", "--disable-dev-shm-usage"]
        )
        context = browser.new_context(
            viewport={"width": 1440, "height": 920},
            device_scale_factor=2
        )
        page = context.new_page()

        # 1. Cyber Forensic Report (Overview + HUD)
        print("Capturing 1/6: preview-forensic-cyber.png...")
        page.goto(f"file://{cyber_html}")
        page.wait_for_selector("#viewer-hud-ribbon")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUTPUT_DIR / "preview-forensic-cyber.png"))

        # 2. Knowledge Inspector Drawer open with CVE Details
        print("Capturing 2/6: preview-inspector-drawer.png...")
        # Open drawer
        page.click("#viewer-hud-ribbon button.action-btn:has-text('Entities')")
        page.wait_for_selector("aside.drawer-container")
        # Click first CVE card
        first_cve = page.locator(".entity-cards-list .entity-item-card:has-text('CVE-')").first
        if first_cve.count() > 0:
            first_cve.click()
            page.wait_for_selector(".entity-hero-card")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUTPUT_DIR / "preview-inspector-drawer.png"))

        # 3. Figure Lightbox Modal
        print("Capturing 3/6: preview-figure-lightbox.png...")
        # Close drawer first
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)
        # Scroll to diagram figure
        fig = page.locator("figure.mermaid-diagram").first
        if fig.count() > 0:
            fig.scroll_into_view_if_needed()
            page.wait_for_timeout(300)
            # Hover over figure to reveal toolbar and click zoom button
            fig.hover()
            zoom_btn = fig.locator("button.fig-btn:has-text('Zoom'), button.fig-btn[title*='Zoom']").first
            if zoom_btn.count() > 0:
                zoom_btn.click()
                page.wait_for_selector(".lightbox-overlay, .figure-lightbox, .lightbox-backdrop")
                page.wait_for_timeout(500)
                page.screenshot(path=str(OUTPUT_DIR / "preview-figure-lightbox.png"))
                page.keyboard.press("Escape")
                page.wait_for_timeout(200)

        # 4. Review & Collaborative Margin Comments
        print("Capturing 4/6: preview-review-annotations.png...")
        page.goto(f"file://{svj_html}")
        page.wait_for_selector("#viewer-hud-ribbon")
        # Open drawer to Review/Notes tab
        notes_btn = page.locator("#viewer-hud-ribbon button.action-btn:has-text('Notes')").first
        if notes_btn.count() > 0:
            notes_btn.click()
            page.wait_for_selector("aside.drawer-container")
            page.wait_for_selector(".annotation-card")
        page.wait_for_timeout(500)
        page.screenshot(path=str(OUTPUT_DIR / "preview-review-annotations.png"))
        page.keyboard.press("Escape")
        page.wait_for_timeout(200)

        # 5. Academic Lecture Handout (FI MUNI theme)
        print("Capturing 5/6: preview-academic-lecture.png...")
        page.goto(f"file://{academic_html}")
        page.wait_for_selector("#title-block-header")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUTPUT_DIR / "preview-academic-lecture.png"))

        # 6. SVJ Invitation & Formal Notice
        print("Capturing 6/6: preview-svj-invitation.png...")
        page.goto(f"file://{svj_html}")
        page.wait_for_selector(".report-content")
        page.wait_for_timeout(400)
        page.screenshot(path=str(OUTPUT_DIR / "preview-svj-invitation.png"))

        browser.close()
        print(f"All 6 preview screenshots saved successfully in {OUTPUT_DIR}/")

if __name__ == "__main__":
    generate_screenshots()
