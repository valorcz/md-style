# Handoff Report: Explorer M1.1 - Air-Gap Enforcement & Offline Testing Architecture

## 1. Observation

### 1.1 Existing Unit Test Suite Health & Baseline
- **Execution Command**: `uv run pytest`
- **Observed Result**:
  ```text
  ============================== 87 passed in 5.02s ==============================
  ```
  Exactly 87 tests passed across 18 test files (`test_bundler.py`, `test_callout_plugin.py`, `test_cleanup.py`, `test_cwe_resolver.py`, `test_d2_diagrams.py`, `test_diagrams.py`, `test_font_bundling.py`, `test_i18n.py`, `test_icons.py`, `test_kb_lifecycle.py`, `test_kb_resolvers.py`, `test_loaders.py`, `test_paged_theme.py`, `test_pandoc_compat.py`, `test_parser.py`, `test_pygments_highlighting.py`, `test_style_remediation.py`, `test_themes.py`).
- Zero regressions currently exist in the baseline suite.

### 1.2 Target Pipeline Network Leak Vectors Observed

#### Vector A: Reverse DNS Queries in `core/kb/resolvers/ip_resolver.py`
- **Location**: `core/kb/resolvers/ip_resolver.py:156-165`
- **Code**:
  ```python
  156:     def resolve(self, token: str, allow_online: bool = True, force_refresh: bool = False) -> Optional[Entity]:
  ...
  163:         classification = self._classify_ip(ip_obj)
  164:         ptr_host = self._resolve_ptr(clean_ip)
  ```
- **Observation**:
  `_resolve_ptr(clean_ip)` calls `socket.gethostbyaddr(ip_str)` (line 133) unconditionally. Even when `allow_online=False`, the reverse DNS PTR lookup is executed over the network. In an air-gapped forensic triage environment, this leaks target IPs to DNS recursors and causes network timeouts.
- **Empirical Proof**:
  Running `ReportEngine` with `PipelineConfig(allow_online=False)` on a document containing `198.51.100.25` intercepted an active call to `socket.gethostbyaddr('198.51.100.25')`.

#### Vector B: Cold-Cache Font Downloading in `core/fonts.py`
- **Location**: `core/fonts.py:27-88`
- **Code**:
  ```python
  27: class FontBundler:
  30:     def __init__(self, cache_dir: Path = FONTS_CACHE_DIR):
  ...
  40:     def fetch_css_import(self, url: str) -> Optional[str]:
  ...
  64:     def fetch_font_binary(self, url: str) -> Optional[bytes]:
  ...
  151:         # If failed, leave original url
  152:         return match.group(0)
  ```
- **Observation**:
  `FontBundler.__init__` does not accept `allow_online`. When `fetch_css_import()` or `fetch_font_binary()` encounters a cold cache (or missing file), it unconditionally executes `urllib.request.urlopen(req, timeout=...)` to Google Fonts (`fonts.googleapis.com` / `fonts.gstatic.com`). Furthermore, when font binary downloading fails offline, line 152 leaves the original `https://fonts.gstatic.com/...` URL in the `@font-face` rule inside the compiled HTML bundle, violating deliverable air-gap purity.
- **Remote Font Usages in Themes**:
  - `styles/base/base.css:7` (`JetBrains Mono`)
  - `styles/base/fonts.css:2` (`JetBrains Mono`, `Merriweather`, `Roboto Slab`)
  - `styles/forensic/cyber/cyber.css:1` (`Inter`, `JetBrains Mono`)
  - `styles/svj/typewriter/typewriter.css:7` (`Courier Prime`)
  - `styles/general/family-invite/family-invite.css:9` (`Playfair Display`, `Plus Jakarta Sans`, `JetBrains Mono`)

#### Vector C: Primer Octicons Remote Fetch in `core/icons.py`
- **Location**: `core/icons.py:19-75`
- **Code**:
  ```python
  19: class IconService:
  22:     def __init__(self, icons_dir: Path = ICONS_DIR, cache_dir: Path = ICON_CACHE_DIR):
  ...
  62:         remote_url = f"https://raw.githubusercontent.com/primer/octicons/main/icons/{clean_name}-16.svg"
  ...
  68:             with urllib.request.urlopen(req, timeout=3) as resp:
  ```
- **Observation**:
  `IconService` does not accept `allow_online`. For any icon not in `data/icons/` or disk cache, it unconditionally attempts an HTTP GET request to `raw.githubusercontent.com`.

#### Vector D: Bundler Disconnection in `core/bundler.py`
- **Location**: `core/bundler.py:28-32`
- **Code**:
  ```python
  28:     def __init__(self, doc_path: Path):
  29:         self.doc_path = doc_path
  30:         self.doc_dir = doc_path.parent
  31:         self.font_bundler = FontBundler()
  ```
- **Observation**:
  `AssetBundler.__init__` does not accept `allow_online` and instantiates `FontBundler()` with default settings. `core/engine.py:258` calls `AssetBundler(input_file)` without passing `allow_online=self.config.allow_online`.

#### Vector E: Interactive Svelte Viewer Offline Purity
- **Location**: `viewer/src/` and `core/assets/viewer.bundle.js`
- **Observation**:
  Verification confirms `viewer/src/` contains 0 instances of `fetch()`, `XMLHttpRequest`, or `WebSocket`. All references to `.fetch()` in `viewer.bundle.js` are internal KaTeX lexer token stream methods (`this.fetch()`). The interactive viewer operates 100% offline from `#md-style-kb-data`, `#md-style-i18n`, and `#md-style-annotations` embedded `<script>` blocks.

---

## 2. Logic Chain

1. **Premise 1 (R3 Air-Gap Requirement)**: The compilation pipeline and bundled outputs must guarantee zero runtime external WAN network requests when `--offline` / `allow_online=False` is active.
2. **Step 2 (IP Resolver Remediation)**: In `core/kb/resolvers/ip_resolver.py:164`, guarding `ptr_host = self._resolve_ptr(clean_ip) if allow_online else None` ensures that reverse DNS lookups are completely bypassed in offline mode while preserving IP entity classification and formatting.
3. **Step 3 (Font Bundling Remediation)**: Adding `allow_online: bool = True` to `FontBundler.__init__`, checking `if not self.allow_online: return None` before network calls in `fetch_css_import()` and `fetch_font_binary()`, replacing offline `@import` with a comment, and substituting unresolvable font URLs in `embed_fonts()` with `local("")` guarantees:
   - Zero network calls on cold cache.
   - Clean retrieval from local cache if warm.
   - Output HTML contains zero external WAN URLs.
4. **Step 4 (Icon Service Remediation)**: Adding `allow_online: bool = True` to `IconService.__init__` and guarding Step 3 behind `if self.allow_online:` guarantees that missing/unknown icons gracefully fall back to the offline vector SVG circle without HTTP traffic.
5. **Step 5 (Pipeline Integration)**: Forwarding `allow_online=self.config.allow_online` from `core/engine.py` through `MarkdownParser` to `IconService`, and through `AssetBundler` to `FontBundler` and `IconService`, establishes an unbroken propagation chain across all 5 compilation stages.
6. **Step 6 (Zero Regression Guarantee)**: Setting default `allow_online=True` on all modified `__init__` signatures ensures that all 87 existing unit tests (which instantiate these classes without `allow_online`) continue to pass with zero disruption.

---

## 3. Caveats

1. **Loopback IPC Exemption**:
   Local loopback (`127.0.0.1`, `::1`, `localhost`, and Unix domain sockets) is required for Chromium DevTools Protocol (`viewer/scripts/print-pdf.mjs:93` connects to `http://127.0.0.1:${port}/json`). The air-gap test fixture must whitelist loopback while strictly blocking all WAN destinations.
2. **Local Font Cache Isolation**:
   The user's environment has pre-cached fonts at `~/.cache/md-style/fonts/`. Automated air-gap tests must point `FONTS_CACHE_DIR` to a temporary empty directory to guarantee that cold-cache execution does not trigger network downloads.
3. **Mermaid Rendering via Bun/Node**:
   Mermaid diagram rendering uses local headless Chromium (`@mermaid-js/mermaid-cli`) over local IPC; it requires no external WAN connectivity.

---

## 4. Conclusion & Actionable Implementation Blueprint

### 4.1 Exact Code Modifications

#### Modification 1: `core/kb/resolvers/ip_resolver.py`
In `resolve()` around line 164:
```python
<<<< PREVIOUS
        classification = self._classify_ip(ip_obj)
        ptr_host = self._resolve_ptr(clean_ip)
==== REPLACEMENT
        classification = self._classify_ip(ip_obj)
        ptr_host = self._resolve_ptr(clean_ip) if allow_online else None
>>>>
```

#### Modification 2: `core/fonts.py`
In `FontBundler`:
```python
<<<< PREVIOUS
    def __init__(self, cache_dir: Path = FONTS_CACHE_DIR):
        self.cache_dir = cache_dir
        self.css_cache_dir = cache_dir / "css"
==== REPLACEMENT
    def __init__(self, cache_dir: Path = FONTS_CACHE_DIR, allow_online: bool = True):
        self.cache_dir = cache_dir
        self.allow_online = allow_online
        self.css_cache_dir = cache_dir / "css"
>>>>
```

In `fetch_css_import()` after checking `cached_css.is_file()`:
```python
<<<< PREVIOUS
        if cached_css.is_file():
            try:
                return cached_css.read_text(encoding="utf-8")
            except Exception:
                pass

        try:
            req = urllib.request.Request(
==== REPLACEMENT
        if cached_css.is_file():
            try:
                return cached_css.read_text(encoding="utf-8")
            except Exception:
                pass

        if not self.allow_online:
            return None

        try:
            req = urllib.request.Request(
>>>>
```

In `fetch_font_binary()` after checking `cached_file.is_file()`:
```python
<<<< PREVIOUS
        if cached_file.is_file():
            try:
                return cached_file.read_bytes()
            except Exception:
                pass

        try:
            req = urllib.request.Request(
==== REPLACEMENT
        if cached_file.is_file():
            try:
                return cached_file.read_bytes()
            except Exception:
                pass

        if not self.allow_online:
            return None

        try:
            req = urllib.request.Request(
>>>>
```

In `inline_imports()`:
```python
<<<< PREVIOUS
                fetched = self.fetch_css_import(target)
                if fetched:
                    # Recursively resolve any nested imports
                    return self.inline_imports(fetched, base_dir)
                return f"/* Failed to import {target} */"
==== REPLACEMENT
                fetched = self.fetch_css_import(target)
                if fetched:
                    # Recursively resolve any nested imports
                    return self.inline_imports(fetched, base_dir)
                if not self.allow_online:
                    return f"/* Offline: skipped import {target} */"
                return f"/* Failed to import {target} */"
>>>>
```

In `embed_fonts()`:
```python
<<<< PREVIOUS
            if binary_data:
                b64_str = base64.b64encode(binary_data).decode("ascii")
                return f'url("data:{mime};base64,{b64_str}")'

            # If failed, leave original url
            return match.group(0)
==== REPLACEMENT
            if binary_data:
                b64_str = base64.b64encode(binary_data).decode("ascii")
                return f'url("data:{mime};base64,{b64_str}")'

            # If remote font failed or offline, avoid leaving WAN url in output
            if url.startswith("http://") or url.startswith("https://"):
                return 'local("")'

            # If failed, leave original url
            return match.group(0)
>>>>
```

#### Modification 3: `core/icons.py`
In `IconService`:
```python
<<<< PREVIOUS
    def __init__(self, icons_dir: Path = ICONS_DIR, cache_dir: Path = ICON_CACHE_DIR):
        self.icons_dir = icons_dir
        self.cache_dir = cache_dir
==== REPLACEMENT
    def __init__(self, icons_dir: Path = ICONS_DIR, cache_dir: Path = ICON_CACHE_DIR, allow_online: bool = True):
        self.icons_dir = icons_dir
        self.cache_dir = cache_dir
        self.allow_online = allow_online
>>>>
```

In `get_svg()` Step 3:
```python
<<<< PREVIOUS
        # 3. Remote fallback from GitHub Primer Octicons
        remote_url = f"https://raw.githubusercontent.com/primer/octicons/main/icons/{clean_name}-16.svg"
        try:
            req = urllib.request.Request(
                remote_url,
                headers={"User-Agent": "Antigravity-Tooling/2.0 (Icon Loader)"}
            )
            with urllib.request.urlopen(req, timeout=3) as resp:
                downloaded_svg = resp.read().decode("utf-8")
            if downloaded_svg and "<svg" in downloaded_svg:
                cache_path.write_text(downloaded_svg, encoding="utf-8")
                self._memory_cache[clean_name] = downloaded_svg
                return self._format_svg(downloaded_svg, extra_classes)
        except Exception:
            pass
==== REPLACEMENT
        # 3. Remote fallback from GitHub Primer Octicons
        if self.allow_online:
            remote_url = f"https://raw.githubusercontent.com/primer/octicons/main/icons/{clean_name}-16.svg"
            try:
                req = urllib.request.Request(
                    remote_url,
                    headers={"User-Agent": "Antigravity-Tooling/2.0 (Icon Loader)"}
                )
                with urllib.request.urlopen(req, timeout=3) as resp:
                    downloaded_svg = resp.read().decode("utf-8")
                if downloaded_svg and "<svg" in downloaded_svg:
                    cache_path.write_text(downloaded_svg, encoding="utf-8")
                    self._memory_cache[clean_name] = downloaded_svg
                    return self._format_svg(downloaded_svg, extra_classes)
            except Exception:
                pass
>>>>
```

#### Modification 4: `core/bundler.py`
```python
<<<< PREVIOUS
from core.fonts import FontBundler
from core.i18n import I18nCatalog
from core.diagnostics import Diagnostics

ASSETS_DIR = Path(__file__).parent / "assets"

class AssetBundler:
    """Bundles HTML fragments, styles, KB data, i18n, fonts, and scripts into a standalone offline HTML document."""

    def __init__(self, doc_path: Path):
        self.doc_path = doc_path
        self.doc_dir = doc_path.parent
        self.font_bundler = FontBundler()
==== REPLACEMENT
from core.fonts import FontBundler
from core.icons import IconService
from core.i18n import I18nCatalog
from core.diagnostics import Diagnostics

ASSETS_DIR = Path(__file__).parent / "assets"

class AssetBundler:
    """Bundles HTML fragments, styles, KB data, i18n, fonts, and scripts into a standalone offline HTML document."""

    def __init__(self, doc_path: Path, allow_online: bool = True):
        self.doc_path = doc_path
        self.doc_dir = doc_path.parent
        self.allow_online = allow_online
        self.font_bundler = FontBundler(allow_online=allow_online)
        self.icon_service = IconService(allow_online=allow_online)
>>>>
```

#### Modification 5: `core/parser/engine.py`
```python
<<<< PREVIOUS
        style_family: Optional[str] = None,
        enable_mermaid: bool = True,
        theme_name: str = "zinc-light",
    ):
        self.lang = lang
        self.catalog = catalog or I18nCatalog(lang)
        self.icon_service = icon_service or IconService()
==== REPLACEMENT
        style_family: Optional[str] = None,
        enable_mermaid: bool = True,
        theme_name: str = "zinc-light",
        allow_online: bool = True,
    ):
        self.lang = lang
        self.catalog = catalog or I18nCatalog(lang)
        self.allow_online = allow_online
        self.icon_service = icon_service or IconService(allow_online=allow_online)
>>>>
```

#### Modification 6: `core/engine.py`
In `ReportEngine.run()`:
- Line 128: `temp_parser = MarkdownParser(allow_online=self.config.allow_online)`
- Line 220: Pass `allow_online=self.config.allow_online` to `MarkdownParser(...)`
- Line 258: `bundler = AssetBundler(input_file, allow_online=self.config.allow_online)`

---

### 4.2 Complete Artifacts Provided in Explorer Directory

1. **Diff Patch**:
   - Path: `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m1_1/airgap.patch`
   - Covers: `core/kb/resolvers/ip_resolver.py`, `core/fonts.py`, `core/icons.py`, `core/bundler.py`, `core/parser/engine.py`, `core/engine.py`.
2. **Automated Test Suite**:
   - Path: `/home/valor/Devel/personal/md-style/.agents/teamwork/explorer_m1_1/proposed_test_airgap_offline.py`
   - Intended Destination: `tests/test_airgap_offline.py`
   - Test Cases (8):
     - `test_offline_ip_resolver_zero_network`: Verifies `198.51.100.25`, `8.8.8.8`, `192.168.1.1` in offline mode.
     - `test_offline_font_bundler_cold_cache`: Verifies `@import` suppression and `@font-face` URL replacement on empty cache.
     - `test_offline_font_bundler_warm_cache`: Verifies offline reading from pre-existing local disk cache.
     - `test_offline_icon_service_fallback`: Verifies local SVG resolution and offline fallback circle SVG.
     - `test_offline_knowledge_resolvers_stubs`: Verifies offline fallbacks for CVE, GHSA, CWE, EVTX.
     - `test_offline_report_engine_compilation_all_themes` (parametrized over 6 themes): Full end-to-end compilation with cold font cache.
     - `test_offline_html_bundle_clean_airgap_deliverable`: Structural regex checks for 0 remote scripts, 0 remote links, 0 remote `@import`, 0 remote fonts.
     - `test_cli_offline_flag_configuration`: Verifies CLI `--offline` flag parsing.

---

## 5. Verification Method

Once the implementer applies `airgap.patch` and installs `tests/test_airgap_offline.py`:

1. **Verify Baseline Unit Tests Health (Zero Regressions)**:
   ```bash
   uv run pytest tests/test_*.py --ignore=tests/test_airgap_offline.py
   ```
   *Expected*: Exactly 87 passed.

2. **Run Air-Gap Offline Test Suite**:
   ```bash
   uv run pytest tests/test_airgap_offline.py -v
   ```
   *Expected*: All 13 tests (8 standalone + 5 parametrized theme variations) pass in < 3 seconds with zero network violations.

3. **Combined Test Execution**:
   ```bash
   uv run pytest
   ```
   *Expected*: Exactly 100 passed (87 baseline + 13 offline airgap tests).

4. **Invalidation Conditions**:
   - Any external socket connect, DNS PTR lookup, or HTTP GET call raises `ConnectionRefusedError("Air-gap violation: ...")`, failing the test suite immediately.
   - Any remote `<script src="http...">`, `<link href="http...">`, `@import url("http...")`, or un-embedded font binary in the HTML deliverable fails the test assertions.
