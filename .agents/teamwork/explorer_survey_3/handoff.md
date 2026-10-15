# Handoff Report: Survey 3 - Core Compilation Pipeline Architecture, Air-Gap Strictness & Test Suite (R3)

## 1. Observation

### 1.1 Existing Unit Test Suite Health & Baseline
- **Location**: 87 tests located in `tests/` across 18 test files:
  - `test_bundler.py` (1 test)
  - `test_callout_plugin.py` (5 tests)
  - `test_cleanup.py` (2 tests)
  - `test_cwe_resolver.py` (4 tests)
  - `test_d2_diagrams.py` (4 tests)
  - `test_diagrams.py` (5 tests)
  - `test_font_bundling.py` (1 test)
  - `test_i18n.py` (5 tests)
  - `test_icons.py` (2 tests)
  - `test_kb_lifecycle.py` (5 tests)
  - `test_kb_resolvers.py` (15 tests)
  - `test_loaders.py` (2 tests)
  - `test_paged_theme.py` (11 tests)
  - `test_pandoc_compat.py` (5 tests)
  - `test_parser.py` (4 tests)
  - `test_pygments_highlighting.py` (3 tests)
  - `test_style_remediation.py` (10 tests)
  - `test_themes.py` (3 tests)
- **Execution Command**: `uv run pytest`
- **Result**: Exactly 87 tests collected, 87 passed in 4.89s (Python 3.14.8, pytest-9.1.1). Zero regressions currently exist in the baseline suite.

### 1.2 Modular Compilation Pipeline Architecture
- **Pipeline Orchestrator** (`core/engine.py`):
  - `PipelineConfig` dataclass defines execution parameters.
    - Line 42: `highlight_style: str = "kate"`.
      - **Defect Observed**: When `PipelineConfig` is instantiated programmatically without overriding `highlight_style`, Pygments 2.17+ raises `pygments.util.ClassNotFound: Could not find style module 'pygments.styles.kate'`. (The CLI works around this by passing `None`, which falls back to the theme default `"one-dark"`).
    - Line 49: `allow_online: bool = True`. In CLI (`core/cli.py:84`), `--offline` flips this to `False`, but online mode is enabled by default.
  - Stage Timers (lines 163–290):
    - **Defect Observed**: Stage 1 timer starts and stops immediately with an empty body (`timer.start("stage1")` at line 163, `timer.stop("stage1")` at line 164). Document validation and reading occur before `stage1` timing begins.
    - Timing metrics are only reported for Stage 2 and Total duration in normal CLI mode; verbose mode does not output a structured per-stage timing breakdown.
  - PDF Compilation & Exit Code Failure (`core/engine.py:300-364`):
    - **Defect Observed**: When `generate_pdf=True`, if the Node/Bun CDP printer script fails AND fallback Chromium browsers fail (or are missing), line 363 calls `Diagnostics.error("No suitable Chromium browser found for PDF export.")` but does not raise an exception. Line 287 unlinks `target_html`. `engine.run()` returns the non-existent destination PDF path, and `core/cli.py` exits with code `0`. A failed PDF build thus silently exits with code 0!
- **Asset Bundler** (`core/bundler.py`):
  - Inlines CSS, base64 fonts, base64 images, embedded JSON manifests (`#md-style-kb-data`, `#md-style-i18n`, `#md-style-source-markdown`, `#md-style-print-templates`), and Svelte viewer code.
  - `AssetBundler.__init__` does not accept `allow_online` or offline configuration and unconditionally instantiates `self.font_bundler = FontBundler()`.

### 1.3 Air-Gap Strictness & Network Leak Analysis
Direct verification was performed on network access vectors:
1. **Unconditional Reverse DNS Queries in IpResolver** (`core/kb/resolvers/ip_resolver.py:128-136, 164`):
   - Line 164: `ptr_host = self._resolve_ptr(clean_ip)`.
   - Line 133: `name, _, _ = socket.gethostbyaddr(ip_str)`.
   - **Empirical Test**: When compiling an uncached document containing `8.8.8.8` with `allow_online=False`, `socket.gethostbyaddr('8.8.8.8')` was actively called over the network. In an air-gapped forensic environment, this leaks target IPs to local/upstream DNS resolvers and causes socket timeouts (1.2s timeout per IP).
2. **Font Inliner Network Calls on Uncached/Cold Builds** (`core/fonts.py:40-88`):
   - `FontBundler.fetch_css_import()` (lines 40-62) and `fetch_font_binary()` (lines 64-88) make HTTP GET requests via `urllib.request.urlopen` (timeout 5s and 8s respectively).
   - Remote Google Fonts are referenced in 5 theme files:
     - `styles/base/base.css` (`JetBrains Mono`)
     - `styles/base/fonts.css` (`JetBrains Mono`, `Merriweather`, `Roboto Slab`)
     - `styles/forensic/cyber/cyber.css` (`Inter`, `JetBrains Mono`)
     - `styles/svj/typewriter/typewriter.css` (`Courier Prime`)
     - `styles/general/family-invite/family-invite.css` (`Playfair Display`, `Plus Jakarta Sans`, `JetBrains Mono`)
   - Fonts were previously cached at `~/.cache/md-style/fonts/` on the local machine on Oct 9, masking network calls.
   - **Empirical Test**: When clearing font cache or running on a cold environment with `allow_online=False`, `FontBundler` ignores offline mode and issues HTTP requests to `https://fonts.googleapis.com/...`, emitting warnings and leaving `/* Failed to import ... */`.
3. **Icon Service Remote Primer Octicons Fetch** (`core/icons.py:62-75`):
   - Line 62: If an icon is not in memory, `static/icons/`, or `cache_dir`, it queries `https://raw.githubusercontent.com/primer/octicons/main/icons/{clean_name}-16.svg`.
   - `IconService` has no `allow_online` parameter and unconditionally attempts network access.
4. **Svelte Viewer Runtime** (`viewer/src/` & `core/assets/viewer.bundle.js`):
   - Grep search for `fetch`, `XMLHttpRequest`, `WebSocket`, `http://`, `https://` confirms zero runtime outbound requests. The viewer operates completely offline from embedded JSON DOM script blocks.

### 1.4 Parser Resilience on Malformed Inputs
Empirical test suite executed via `uv run python` on `MarkdownParser` (`core/parser/engine.py`):
1. **Unclosed Frontmatter**:
   - Input: Document starting with `---` without closing `---`.
   - Result: `parse_frontmatter` safely detects `len(parts) < 3`, returns `cleaned_src=src, meta={}`, and parses entire content as standard Markdown without exceptions.
2. **Invalid YAML Syntax**:
   - Input: `title: [unclosed list\ninvalid: : :`.
   - Result: `yaml.safe_load` catches syntax error, logs `Diagnostics.warn`, returns `meta={}`, and document renders safely.
3. **Unmatched Code Fences**:
   - Input: ```` ```python ```` without terminating triple backticks.
   - Result: Markdown-it captures code block up to EOF; renders `<pre class="highlight-code">` cleanly without syntax or parser failure.
4. **Deeply Nested Pandoc Fenced Divs**:
   - Input: 5 levels of nested `:::::` / `::::` / `:::`.
   - Result: All divs balance cleanly (count `<div` matches count `</div>`). Unclosed containers are auto-terminated at EOF.
5. **Nested Blockquote Callouts Defect** (`core/parser/plugins/callouts.py:81-185`):
   - Input: `> [!NOTE] Level 1\n> > [!WARNING] Level 2\n> > > [!CRITICAL] Level 3`.
   - **Defect Observed**: While Level 1 is transformed into `<div class="callout callout-note">`, inner blockquotes are NOT recursively parsed. They are output as raw `<blockquote><p>[!WARNING] Level 2</p></blockquote>`.
6. **Callout Header/Body Text Duplication** (`core/parser/plugins/callouts.py:96-162`):
   - **Defect Observed**: In single-line alerts (`> [!NOTE] Custom Title`), `Custom Title` is extracted as the callout header title, but is NOT removed from `inline_tok.content`. The title string is rendered twice: once in `<span class="callout-title">Custom Title</span>` and once in `<div class="callout-content"><p>Custom Title</p></div>`.

### 1.5 Documentation Architecture Discrepancy
- Documentation files in `docs/` (`docs/architecture.md`, `docs/index.md`, `docs/knowledge-base.md`, `docs/style-development.md`) still describe the legacy v2 architecture (Pandoc multi-pass Lua filters, `styles/*.lua`, `knowledge-manifest.json`, `data/cache/`).
- `md-style` v3 is Pure-Python (`markdown-it-py` + `mdit_py_plugins` + Svelte 5 viewer), and no longer depends on Pandoc or Lua filters.
- There is currently no R3 audit report document in `docs/`.

---

## 2. Logic Chain

1. **Air-Gap Strictness**:
   - *Premise*: Requirement R3 requires zero runtime external network requests across all themes and bundled deliverables, guaranteed by an automated offline test.
   - *Observation*: `IpResolver._resolve_ptr` calls `socket.gethostbyaddr` unconditionally; `FontBundler` and `IconService` make HTTP requests on cache misses because they do not receive `allow_online`.
   - *Inference*: Even if `--offline` is passed on the command line, the compilation pipeline is NOT strictly air-gapped when encountering uncached IPs, uncached icons, or uncached fonts.
   - *Solution*: `allow_online` must be propagated to `FontBundler` and `IconService`, and `IpResolver` must guard `self._resolve_ptr` behind `if allow_online:`. When `allow_online=False`, all remote fetching must short-circuit, and missing assets must fall back to local SVG/fonts.

2. **Parser Hardening**:
   - *Premise*: Requirement R3 requires resilience against malformed inputs and deeply nested callouts.
   - *Observation*: While frontmatter, unclosed code fences, and Pandoc divs handle malformed syntax without crashing, nested blockquote alerts fail to transform inner alerts, and single-line alerts duplicate the title in the body.
   - *Solution*: `transform_blockquote_callouts` must recursively process inner tokens to support arbitrary alert nesting, and single-line alert title extraction must cleanly separate title from body tokens.

3. **CLI Determinism & Exit Codes**:
   - *Premise*: Pipeline must ensure consistent cross-platform exit codes and accurate build timing metrics.
   - *Observation*: `PipelineConfig` defaults `highlight_style="kate"` (crashing programmatic instantiation), `_compile_pdf` exits with code 0 on Chromium failure, and Stage 1 timer measures 0.00s.
   - *Solution*: Set default `highlight_style=None` in `PipelineConfig`; raise `RuntimeError` on failed PDF generation so `cli.py` exits with code 1; start Stage 1 timer before file validation/reading; print structured timing breakdown in verbose mode.

---

## 3. Caveats

1. **Chromium CDP Loopback Communication**:
   - The PDF generation bridge (`viewer/scripts/print-pdf.mjs:93`) uses `fetch('http://127.0.0.1:${port}/json')` to interact with Chromium DevTools Protocol over local loopback.
   - An air-gap test that blocks all network traffic must allow loopback (`127.0.0.1` / `::1`) or intercept at the socket layer to distinguish local CDP inter-process communication from external WAN requests.
2. **Pre-Seeded Font Cache**:
   - The user's local cache (`~/.cache/md-style/fonts/`) contains pre-cached WOFF2 files. Any offline test must run against an isolated/mocked cache directory to prove that cold-cache offline compilation does not trigger external downloads.
3. **Mermaid Diagram External Tools**:
   - Static Mermaid rendering (`core/diagrams/mermaid.py`) relies on `@mermaid-js/mermaid-cli` executed via Bun or Node. It renders diagrams locally via headless Chromium without external network calls.

---

## 4. Conclusion & Actionable Recommendations

To satisfy Requirement R3 and its acceptance criteria, the implementer agent should execute the following changes:

### Phase 1: Pipeline Hardening
1. **`core/engine.py`**:
   - Change `PipelineConfig.highlight_style` default from `"kate"` to `None`.
   - Move `self.timer.start("stage1")` to line 114 (before `validate_input_file` and reading `raw_content`).
   - In `_compile_pdf()`, if both CDP script and browser fallback fail, raise `RuntimeError("PDF export failed: No suitable Chromium browser found or printer script returned an error.")` instead of silently returning.
   - In `run()`, when `--verbose` is set, print a structured 5-stage timing breakdown:
     - Stage 1 (Validation & Ingestion): X.XXs
     - Stage 2 (Knowledge Pack Sync): X.XXs
     - Stage 3 (Theme Resolution): X.XXs
     - Stage 4 (Markdown AST & Transforms): X.XXs
     - Stage 5 (Output Bundling & Export): X.XXs
2. **`core/kb/resolvers/ip_resolver.py`**:
   - In `resolve()`, guard line 164:
     ```python
     ptr_host = self._resolve_ptr(clean_ip) if allow_online else None
     ```
3. **`core/fonts.py`**:
   - Add `allow_online: bool = True` to `FontBundler.__init__`.
   - In `fetch_css_import()` and `fetch_font_binary()`, if `not self.allow_online`, return `None` immediately without attempting `urllib.request.urlopen`.
   - In `embed_fonts()`, if binary font cannot be resolved offline, strip the remote URL or replace with a local fallback notice rather than leaving raw `https://fonts.gstatic.com/...` in the output HTML.
4. **`core/icons.py`**:
   - Add `allow_online: bool = True` to `IconService.__init__`.
   - In `get_svg()`, if `not self.allow_online`, skip Step 3 (GitHub CDN fetch) and immediately return the local generic fallback SVG (Step 4).
5. **`core/bundler.py`**:
   - Accept `allow_online: bool = True` in `AssetBundler.__init__` and pass it to `self.font_bundler = FontBundler(allow_online=allow_online)`.
   - Forward `allow_online=self.config.allow_online` from `core/engine.py:258`.
6. **`core/parser/plugins/callouts.py`**:
   - Update `transform_blockquote_callouts`:
     - Recursively call `transform_blockquote_callouts` on inner tokens collected between `blockquote_open` and `blockquote_close` to support deeply nested callout hierarchies.
     - For single-line callouts, strip `custom_title` from the paragraph inline content so the title is not duplicated in the callout body.

### Phase 2: Automated Offline & Air-Gap Test Suite
Create `tests/test_airgap_offline.py`:
1. Use `monkeypatch` to intercept `socket.socket.connect` and `urllib.request.urlopen`:
   - Whitelist only loopback (`127.0.0.1`, `::1`) for CDP browser control.
   - For any other destination IP or URL, raise a `ConnectionRefusedError("Air-gap violation: external network request attempted")`.
2. Test cases to verify:
   - Compiling a document with uncached IPs (`194.26.29.114`, `8.8.8.8`) with `--offline` / `allow_online=False` completes with 0 network calls.
   - Compiling documents across all themes with cold/empty font cache in offline mode completes without network calls.
   - Uncached CVE, GHSA, CWE, and EVTX tokens in offline mode return clean offline stubs with 0 network calls.
   - Exported HTML bundle contains zero remote `<script src="http...">`, zero `<link href="http...">`, and zero `@import url("http...")`.

### Phase 3: Comprehensive Audit Report in `docs/`
Create `docs/pipeline_audit_report.md` covering:
1. Architectural audit of the Pure-Python modular pipeline (Stages 1–5).
2. Air-gap strictness verification and remediation of the reverse DNS / font download leak vectors.
3. Resilience analysis for malformed inputs (frontmatter edge cases, nested callout recursion, unclosed code blocks).
4. CLI diagnostics, exit code determinism, and build performance metrics.
5. Verification matrix confirming 0 regressions across all 87 baseline tests.

---

## 5. Verification Method

To independently verify these findings:

1. **Verify Baseline Test Health**:
   ```bash
   uv run pytest
   ```
   *Expected*: 87 passed.

2. **Verify IP Resolver Reverse DNS Leak**:
   ```bash
   uv run python -c "
   import socket
   from pathlib import Path
   from core.engine import ReportEngine, PipelineConfig

   dns_calls = []
   orig_gethostbyaddr = socket.gethostbyaddr
   def mock_gethostbyaddr(ip):
       dns_calls.append(ip)
       return ('c2.evil.com', [], [ip])
   socket.gethostbyaddr = mock_gethostbyaddr

   src = Path('/tmp/test_leak.md')
   src.write_text('# IP Test\nBeacon observed at 198.51.100.25.\n', encoding='utf-8')
   cfg = PipelineConfig(input_file=src, style='forensic/cyber', highlight_style=None, allow_online=False, quiet=True)
   ReportEngine(cfg).run()
   print('DNS calls made despite allow_online=False:', dns_calls)
   "
   ```
   *Observed*: Prints `['198.51.100.25']`, confirming the active network leak.

3. **Verify Nested Callout Issue**:
   ```bash
   uv run python -c "
   from core.parser import MarkdownParser
   p = MarkdownParser()
   html, _, _ = p.render('> [!NOTE] Outer\n> > [!WARNING] Inner\n> > Content\n')
   print('Inner callout rendered:', 'callout-warning' in html)
   "
   ```
   *Observed*: Prints `Inner callout rendered: False` (inner alert remains a raw blockquote).

4. **Verify PDF Failure Silent Exit Code**:
   ```bash
   uv run python -c "
   from pathlib import Path
   from core.engine import ReportEngine, PipelineConfig
   import unittest.mock

   src = Path('/tmp/test_pdf.md')
   src.write_text('# Test PDF\nContent\n', encoding='utf-8')
   cfg = PipelineConfig(input_file=src, output_file=Path('/tmp/test_fail.pdf'), generate_pdf=True, quiet=True)
   engine = ReportEngine(cfg)
   with unittest.mock.patch('shutil.which', return_value=None):
       engine.run()
   print('PDF exists:', Path('/tmp/test_fail.pdf').is_file())
   "
   ```
   *Observed*: Prints `PDF exists: False`, but no exception was raised and process exited with 0.
