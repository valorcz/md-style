"""
tests/e2e/conftest.py
Playwright configuration and headless browser fixtures for Svelte Viewer E2E tests.

Milestone: M3 (Headless Browser E2E Test Suite - R1).
"""

from __future__ import annotations

import os
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from core.engine import PipelineConfig, ReportEngine


def resolve_chromium_path() -> Optional[str]:
    """
    Locates the Chromium binary on the host machine in priority order:
    1. CHROME_BIN environment variable override
    2. System PATH executables (chromium-browser, chromium, google-chrome)
    3. Canonical Linux package paths (/usr/bin/chromium-browser, /usr/lib64/...)
    4. Playwright cache directory (~/.cache/ms-playwright)
    """
    # 1. Environment variable override
    if env_chrome := os.environ.get("CHROME_BIN"):
        if Path(env_chrome).is_file():
            return env_chrome

    # 2. System PATH lookups
    for name in ("chromium-browser", "chromium", "google-chrome", "google-chrome-stable"):
        if found := shutil.which(name):
            return found

    # 3. Canonical Linux binary paths
    known_paths = [
        "/usr/bin/chromium-browser",
        "/usr/bin/chromium",
        "/usr/lib64/chromium-browser/chromium-browser",
        "/usr/bin/google-chrome",
        "/usr/bin/google-chrome-stable",
        "/snap/bin/chromium",
    ]
    for p in known_paths:
        if Path(p).is_file():
            return p

    # 4. Playwright user cache fallback
    cache_dir = Path.home() / ".cache" / "ms-playwright"
    if cache_dir.is_dir():
        for chrome_bin in cache_dir.glob("chromium-*/chrome-linux64/chrome"):
            if chrome_bin.is_file():
                return str(chrome_bin)

    return None


@pytest.fixture(scope="session")
def browser_type_launch_args() -> Dict[str, Any]:
    """
    Configures browser launch parameters for Playwright.
    Enforces headless mode, Linux sandbox resilience, and offline system Chromium binary.
    """
    launch_args: Dict[str, Any] = {
        "headless": True,
        "args": [
            "--no-sandbox",
            "--disable-setuid-sandbox",
            "--disable-dev-shm-usage",
            "--disable-gpu",
            "--headless=new",
            "--host-resolver-rules=MAP * ^NOTFOUND",
        ],
    }
    chromium_path = resolve_chromium_path()
    if chromium_path:
        launch_args["executable_path"] = chromium_path
    return launch_args


@pytest.fixture(scope="session")
def browser_context_args() -> Dict[str, Any]:
    """
    Configures BrowserContext parameters:
    - Viewport width >= 1360px (1440x900) ensures Margin Gutter cards are rendered
      (MarginGutter.svelte hides cards via media query when viewport width <= 1280px).
    - accept_downloads=True allows intercepting exported HTML and CriticMarkup downloads.
    """
    return {
        "viewport": {"width": 1440, "height": 900},
        "accept_downloads": True,
        "ignore_https_errors": True,
        "bypass_csp": True,
        "locale": "en-US",
    }


class ConsoleTracker:
    """Collects console messages and page errors from Playwright page instance."""

    def __init__(self) -> None:
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.logs: List[str] = []

    def on_console(self, msg: Any) -> None:
        text = f"[{msg.type.upper()}] {msg.text}"
        self.logs.append(text)
        if msg.type == "error":
            self.errors.append(text)
        elif msg.type == "warning":
            self.warnings.append(text)

    def on_page_error(self, exc: Any) -> None:
        self.errors.append(f"[UNCAUGHT_EXCEPTION] {exc}")

    def assert_no_errors(self, context_msg: str = "") -> None:
        if self.errors:
            formatted = "\n".join(f"  - {err}" for err in self.errors)
            msg = f"Unexpected console errors detected {context_msg}:\n{formatted}"
            raise AssertionError(msg)

    def clear(self) -> None:
        self.errors.clear()
        self.warnings.clear()
        self.logs.clear()


@pytest.fixture
def console_tracker(page: Any) -> ConsoleTracker:
    """
    Attaches console and error listeners to the active Playwright page.
    Yields tracker for assertions in tests.
    """
    tracker = ConsoleTracker()
    page.on("console", tracker.on_console)
    page.on("pageerror", tracker.on_page_error)
    return tracker


@pytest.fixture
def console_errors(console_tracker: ConsoleTracker) -> List[str]:
    """Convenience fixture providing direct access to intercepted console errors."""
    return console_tracker.errors


@pytest.fixture(scope="session")
def sample_cyber_html(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """
    Compiles examples/sample-forensic-cyber.md to an isolated temporary HTML file
    using the offline ReportEngine.
    """
    out_dir = tmp_path_factory.mktemp("e2e_fixtures")
    dest_path = out_dir / "sample-forensic-cyber.html"
    src_md = Path("examples/sample-forensic-cyber.md")
    assert src_md.is_file(), f"Sample markdown source not found at {src_md}"

    config = PipelineConfig(
        input_file=src_md,
        output_file=dest_path,
        style="forensic/cyber",
        allow_online=False,
        highlight_style=None,
    )
    engine = ReportEngine(config)
    engine.run()
    assert dest_path.is_file() and dest_path.stat().st_size > 0
    return dest_path


@pytest.fixture(scope="session")
def sample_annotated_html(tmp_path_factory: pytest.TempPathFactory) -> Path:
    """
    Compiles an HTML report with pre-baked baseline annotations in frontmatter.
    Tests script tag re-hydration (#md-style-annotations) and tombstone overrides.
    """
    out_dir = tmp_path_factory.mktemp("e2e_fixtures_ann")
    src_md = out_dir / "annotated-sample.md"
    dest_path = out_dir / "annotated-sample.html"

    content = """---
title: "Baseline Incident Analysis"
style: "forensic/cyber"
case_id: "E2E-TEST-001"
annotations:
  - id: "ann-prebaked-1"
    text: "Initial triage confirmation"
    category: "insight"
    createdAt: "2026-10-11T12:00:00Z"
    author: "Lead Analyst"
    range:
      quote: "Incident Response Summary"
      prefixContext: ""
      suffixContext: ""
      blockIndex: 0
      textOffsetInBlock: 0
  - id: "ann-prebaked-2"
    text: "Note to be deleted via tombstone"
    category: "question"
    createdAt: "2026-10-11T12:05:00Z"
    author: "Peer Reviewer"
    range:
      quote: "Threat Actor Profile"
      prefixContext: ""
      suffixContext: ""
      blockIndex: 1
      textOffsetInBlock: 0
---

# Incident Response Summary

Threat Actor Profile investigation notes.
"""
    src_md.write_text(content, encoding="utf-8")
    config = PipelineConfig(
        input_file=src_md,
        output_file=dest_path,
        style="forensic/cyber",
        allow_online=False,
        highlight_style=None,
    )
    engine = ReportEngine(config)
    engine.run()
    assert dest_path.is_file() and dest_path.stat().st_size > 0
    return dest_path
