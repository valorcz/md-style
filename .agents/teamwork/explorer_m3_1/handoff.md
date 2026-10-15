# Handoff Report: Playwright E2E Environment & `conftest.py` Architecture (Milestone M3 / R1)

**Agent**: `explorer_m3_1`  
**Role**: `teamwork_preview_explorer`  
**Date**: 2026-10-11T15:52:00Z  
**Target Milestone**: M3 (Headless Browser E2E Test Suite - R1)  
**Task Directive**: Technical investigation of Playwright E2E environment, system Chromium availability, headless launch parameters, and `tests/e2e/conftest.py` implementation recipe.

---

## 1. Observation

### 1.1 Python Virtual Environment & Dev Dependencies
- **`pyproject.toml`** (lines 29–33):
  ```toml
  [dependency-groups]
  dev = [
      "pytest>=8.4.2",
  ]
  ```
  Neither `playwright` nor `pytest-playwright` is currently listed in `pyproject.toml`.
- **`.venv` site packages** (`.venv/lib/python3.14/site-packages`):
  Python version is `3.14.8`. Installed packages include `pytest-9.1.1`, `babel-2.18.0`, `jinja2-3.1.6`, `markdown_it_py-4.2.0`, `pygments-2.21.0`, etc. No `playwright` or `pytest-playwright` directories are present.
- **`uv.lock`**:
  Grep search for `playwright` returned 0 matches.
- **Resolution test** (`explorer_survey_1/handoff.md` lines 353–355):
  `uv pip install --dry-run pytest-playwright` resolved `pytest-playwright==0.10.0` and `playwright==1.63.0` on Python 3.14.8 cleanly with 0 dependency conflicts.

### 1.2 Chromium Browser Binaries on Host
- **`/usr/bin/chromium-browser`** (lines 1–52):
  Present on the host filesystem. It is a 52-line bash wrapper script on Fedora (`CHROME_VERSION_EXTRA="Built from source for Fedora release 44"`):
  ```bash
  exec -a "$0" "$HERE/chromium-browser" $CHROMIUM_FLAGS $CHROMIUM_DISTRO_FLAGS "$@"
  ```
  Invoking `/usr/bin/chromium-browser --headless=new --dump-dom "about:blank"` exited with code 0 and dumped valid DOM.
- **`/usr/lib64/chromium-browser/chromium-browser`**:
  Confirmed present (size: 333,230,120 bytes; 333 MB ELF binary). This is the underlying native binary invoked by the `/usr/bin/chromium-browser` wrapper.
- **`/usr/bin/chromium`**:
  Does NOT exist on this machine (`stat /usr/bin/chromium: no such file or directory`).
- **Playwright User Cache** (`/home/valor/.cache/ms-playwright/`):
  Directory contains:
  - `chromium-1243/chrome-linux64/chrome` (size: 293,285,184 bytes; 293 MB ELF binary).
  - `chromium_headless_shell-1243/`
  - `ffmpeg-1011/`
  Both `DEPENDENCIES_VALIDATED` and `INSTALLATION_COMPLETE` marker files are present.

### 1.3 CDP Script & Production Browser Launch Flags
- **`viewer/scripts/print-pdf.mjs`** (lines 74–83):
  The existing high-fidelity PDF printer successfully launches Chromium using:
  ```javascript
  const chromeProc = spawn(browserBin, [
    "--headless=new",
    "--disable-gpu",
    "--no-sandbox",
    "--disable-extensions",
    "--disable-dev-shm-usage",
    `--user-data-dir=${tmpDir}`,
    `--remote-debugging-port=${port}`,
    "about:blank",
  ]);
  ```
- **`core/engine.py`** (lines 394–413):
  Fallback PDF compilation in Python checks `browsers = ["chromium-browser", "chromium", "google-chrome", ...]` using `shutil.which()`.

### 1.4 Svelte Viewer DOM Structure & Responsive Breakpoints
- **Margin Gutter breakpoint** (`viewer/src/annotations/MarginGutter.svelte` lines 53–57 / 119–123):
  ```css
  @media (max-width: 1280px) {
    .margin-gutter {
      display: none !important;
    }
  }
  ```
  At viewport widths $\le 1280$px, `.margin-gutter` is hidden with `display: none !important`. Viewport width must be configured $\ge 1360$px (recommended `1440x900`) for gutter elements to be interactive and visible.
- **Viewer mounting trigger** (`viewer/src/main.ts` lines 16–22):
  Ensures `#md-style-viewer-root` exists on `document.documentElement`, then mounts `App.svelte`.
- **Top-level viewer components** (`viewer/src/App.svelte` lines 370–420):
  Renders `#viewer-hud-ribbon`, `MarginGutter` (when `educativeMode` is active), `AnnotationPopover` (on text selection), and `InspectorDrawer`.
- **Table toolbar injection** (`viewer/src/App.svelte` lines 120–135):
  Iterates over `table` elements with $\ge 4$ rows and mounts `.table-toolbar-container` immediately preceding the table.
- **Clean bundle export** (`viewer/src/annotations/export-bundle.ts` lines 53–64):
  Triggers file download via `<a download="...">` with filename `${docTitle}-annotated.html` using a `blob:` URL.

---

## 2. Logic Chain

1. **Air-Gap Strictness & Offline Execution (R3 & M3)**:
   - Observation 1.1 & 1.2: Both system Chromium (`/usr/bin/chromium-browser`) and cached Playwright Chromium (`~/.cache/ms-playwright/chromium-1243/...`) already exist locally on disk.
   - If Playwright launches without `executable_path` in an environment where cache is missing or cleared, it might attempt to download 150MB from Microsoft CDN over the network, violating the air-gap requirement.
   - Therefore, `tests/e2e/conftest.py` must dynamically resolve local browser binaries (preferring `CHROME_BIN`, `shutil.which("chromium-browser")`, `/usr/bin/chromium-browser`, `/usr/lib64/chromium-browser/chromium-browser`, and `~/.cache/ms-playwright/`), ensuring zero external network requests.
2. **Headless Stability in Linux Environments**:
   - Observation 1.3: The system Chromium wrapper requires `--no-sandbox`, `--disable-dev-shm-usage`, and `--disable-gpu` to prevent sandbox failures, `/dev/shm` shared memory exhaustion, and GPU software rasterizer panics.
   - Using `--headless=new` guarantees that modern web platform APIs (CSS Custom Highlights `CSS.highlights`, Custom Elements, Blob URLs) operate identically to full Chrome.
3. **Viewport Sizing & Layout Fidelity**:
   - Observation 1.4: Margin Gutter cards have `@media (max-width: 1280px) { display: none !important; }`. If tests run on standard 1280px or mobile viewport, comment cards will be hidden and locators will time out.
   - Therefore, `browser_context_args` must mandate a desktop viewport of at least `{"width": 1440, "height": 900}`.
4. **Download Handling for Bundle Export**:
   - Observation 1.4: `exportUpdatedHtmlBundle` downloads the exported document via an ephemeral `<a download>` tag.
   - Playwright context requires `accept_downloads=True` to capture the download event and permit `download.save_as()`.
5. **Console Error & Re-hydration Assertion**:
   - Observation 1.4 & AC 37: Acceptance criteria explicitly mandate that exported bundles re-open with 0 console errors.
   - By creating a `console_tracker` fixture attaching listeners to `page.on("console")` (filtering `msg.type == "error"`) and `page.on("pageerror")` (capturing unhandled JS exceptions), tests can perform deterministic assertions: `console_tracker.assert_no_errors()`.
6. **Fixture Isolation & Reproducibility**:
   - Tests should not rely on pre-existing mutable files in `output/`.
   - Creating session-scoped fixtures `sample_cyber_html` and `sample_annotated_html` using `ReportEngine(PipelineConfig(allow_online=False)).compile(...)` compiles fresh, self-contained HTML files into pytest's temporary directory (`tmp_path_factory`), ensuring 100% test reproducibility.

---

## 3. Caveats

1. **Browser Wrapper vs Binary**: `/usr/bin/chromium-browser` is a bash wrapper script that execs `/usr/lib64/chromium-browser/chromium-browser`. Testing confirmed `/usr/bin/chromium-browser` executes correctly with headless flags. The resolution helper in `conftest.py` supports both.
2. **`file://` Origin for `localStorage`**: Chromium scopes `localStorage` across `file://` URLs to the `file://` origin within a single `BrowserContext`. Because Playwright creates a fresh `BrowserContext` for each test function, `localStorage` is completely isolated between tests. When testing export re-hydration in a clean session, creating a new context via `browser.new_context()` ensures zero storage leakage.
3. **Dependency Sync Required**: Dev dependencies `playwright` and `pytest-playwright` must be synced into `.venv` before running `pytest tests/e2e/`.

---

## 4. Conclusion & Implementation Recipe

To establish a headless Playwright E2E environment for Milestone M3, the following changes are specified:

### 4.1 Dependency Configuration (`pyproject.toml`)
Update `[dependency-groups] dev` in `pyproject.toml`:
```toml
[dependency-groups]
dev = [
    "pytest>=8.4.2",
    "playwright>=1.40.0",
    "pytest-playwright>=0.5.0",
]
```
Execute `uv sync` to install wheels into `.venv`.

### 4.2 Makefile Target
Add `test-e2e` to `Makefile`:
```makefile
test-e2e:
	uv run pytest tests/e2e/ -v
```

### 4.3 `tests/e2e/conftest.py` Complete Blueprint
Create `tests/e2e/conftest.py`:

```python
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
    Guarantees clean, reproducible test input containing:
    - Svelte viewer runtime bundle
    - Multi-row tables for TableToolbar testing
    - Entity tags (.inspectable) for InspectorDrawer testing
    - Rich body text for annotation creation testing
    """
    out_dir = tmp_path_factory.mktemp("e2e_fixtures")
    dest_path = out_dir / "sample-forensic-cyber.html"
    src_md = Path("examples/sample-forensic-cyber.md")
    assert src_md.is_file(), f"Sample markdown source not found at {src_md}"

    engine = ReportEngine(PipelineConfig(allow_online=False, highlight_style=None))
    engine.compile(src_md, dest_path, style="forensic/cyber")
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
    engine = ReportEngine(PipelineConfig(allow_online=False, highlight_style=None))
    engine.compile(src_md, dest_path, style="forensic/cyber")
    assert dest_path.is_file() and dest_path.stat().st_size > 0
    return dest_path
```

---

## 5. Verification Method

To independently verify this environment and recipe:

1. **Verify Chromium Binary Availability**:
   - Inspect `/usr/bin/chromium-browser` and `/usr/lib64/chromium-browser/chromium-browser`.
   - Command:
     ```bash
     /usr/bin/chromium-browser --headless=new --dump-dom "about:blank"
     ```
   - Invalidation condition: Command fails, exits non-zero, or fails to render DOM.

2. **Verify Playwright Dependency Resolution**:
   - Command:
     ```bash
     uv pip install --dry-run pytest-playwright
     ```
   - Invalidation condition: Package resolution conflicts or incompatibility with Python 3.14.

3. **Verify E2E Test Execution Command**:
   - After creating `tests/e2e/conftest.py` and test cases, execute:
     ```bash
     uv run pytest tests/e2e/ -v
     ```
   - Invalidation condition: Browser launch fails or fails to bind fixtures.
